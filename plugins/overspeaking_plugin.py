from chatbot import FeaturePlugin, Message, Author
from collections import defaultdict, deque
from typing import Dict, Any, Union, List
from random import choice
from datetime import datetime

class OverspeakingPlugin(FeaturePlugin):

    def __init__(self, config: dict):
        message_window = int(config["MessageWindow"])
        message_count_threshold = int(config["MessageCountThreshold"])
        if message_window < 1 or message_count_threshold < 1 or message_window < message_count_threshold:
            raise ValueError()
        self.message_window = message_window
        self.message_count_threshold = message_count_threshold
        self.warning_format_strings = config["WarningFormatStrings"]
        self.last_notification = None
        self.notification_threshold = config["NotificationThreshold"]

    @staticmethod
    def get_overspeaking_authors(
            chat_transcript: List[Message],
            author_id_for_chatbot: int,
            message_window_size: int, message_count_threshold: int) -> List[Author]:

        window = deque()
        author_id_to_message_count = defaultdict(lambda: 0)
        author_id_to_accounted_for_ts = defaultdict(lambda: 0)
        author_id_to_author = {}

        for message in chat_transcript:
            author_id_to_author[message.author.id] = message.author
            # Making sure the right message is recorded!
            if message.author.id == author_id_for_chatbot and "Thank you" in message.text:
                for (author_id, count) in author_id_to_message_count.items():
                    if count >= message_count_threshold:
                        author_id_to_message_count[author_id] = 0
                        author_id_to_accounted_for_ts[author_id] = message.timestamp
            else:
                if len(window) == message_window_size:
                    removed_message = window.popleft()
                    message_accounted_for = removed_message.timestamp < author_id_to_accounted_for_ts[
                        removed_message.author.id]
                    if not message_accounted_for and removed_message.author.id != author_id_for_chatbot:
                        author_id_to_message_count[removed_message.author.id] -= 1
                window.append(message)
                if message.author.id != author_id_for_chatbot:
                    author_id_to_message_count[message.author.id] += 1

        return [author_id_to_author[author_id]
                for author_id, message_count in author_id_to_message_count.items()
                if message_count >= message_count_threshold]

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:
        overspeaking_authors = OverspeakingPlugin.get_overspeaking_authors(
            chat_transcript,
            author_id_for_chatbot,
            self.message_window,
            self.message_count_threshold)

        overspeaking_warnings = [{"ephemeral": False, "message": Message(Author(author_id_for_chatbot, "Chatbot"),
                                                                         -1, choice(self.warning_format_strings).format(a.name))}
                                 for a in overspeaking_authors]

        if len(overspeaking_authors) == 0:
            return []

        if self.last_notification is None:
            self.last_notification = datetime.now()
            return overspeaking_warnings

        # check if we sent out a notification from this plugin in the last "notification_threshold" minutes.
        if (datetime.now() - self.last_notification).total_seconds() < self.notification_threshold * 60:
            return []

        # Update last notification.
        self.last_notification = datetime.now()
        return overspeaking_warnings
