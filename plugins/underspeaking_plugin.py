from chatbot import FeaturePlugin, Message, Author
from datetime import datetime, timedelta
from typing import Dict, Any, Union, List
from random import choice


class UnderspeakingPlugin(FeaturePlugin):
    def __init__(self, config: Dict):
        self.message_window = config["MessageWindow"]
        self.warning_strings = config["WarningFormatStrings"]
        self.time_filter = config["TimeFilter"]
        self.last_alert = None

        if self.time_filter:
            self.time_filter_range = config["TimeFilterRangeMinutes"]

        pass

    @staticmethod
    def get_message_count(chat_transcript: List[Message]) -> Dict:
        """
        Using a separate function so that underspeaking counter can be changed
        """
        speech_count = {}
        for chat in chat_transcript:
            speech_count[chat.author.id] = speech_count.get(chat.author.id, 0) + 1

        return speech_count

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        # Filter non-chatbot messages
        # chat_transcript = [x for x in chat_transcript if x.author.id != author_id_for_chatbot]

        reversed_chat = chat_transcript[::-1]

        cur_timestamp = datetime.now()

        # Filter by time if enabled by the user
        if self.time_filter:
            reversed_chat = [x for x in reversed_chat if
                             (cur_timestamp - datetime.fromtimestamp(x.timestamp)).total_seconds() / 60 < self.time_filter_range]
        # Trim to the required window
        reversed_chat = reversed_chat[:self.message_window]

        # If the trimmed window is too small
        if len(reversed_chat) < self.message_window:
            return []

        # Check if we already sent an alert for this time window
        if self.last_alert is not None and self.last_alert > datetime.fromtimestamp(reversed_chat[0].timestamp):
            return []

        speech_count = UnderspeakingPlugin.get_message_count(reversed_chat)

        underspeakers_list = []

        for member, count in speech_count.items():
            if count < (self.message_window / (len(channel_members) * 2)):
                underspeakers_list.append(member)

        if not underspeakers_list:
            return []

        self.last_alert = datetime.now()
        underspeakers_list = ["<@{}>".format(x) for x in underspeakers_list]

        authors = ", ".join(underspeakers_list)

        return [{"ephemeral": False, "message": Message(Author(author_id_for_chatbot, "Chatbot"),
                            -1, "{}".format(choice(self.warning_strings).format(authors)))}]


