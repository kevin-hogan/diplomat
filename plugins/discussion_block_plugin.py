from chatbot import FeaturePlugin, Message, Author
from typing import Dict, Any, Union, List
from datetime import datetime


class DiscussionBlock(FeaturePlugin):

    def __init__(self, config: dict):
        self.config = config
        self.max_sent_times = config.get("max_sent_times", 1)
        self.silence_time = config.get("silence_threshold")
        self.send_counter = 0

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        last_message_time = None

        if self.send_counter >= self.max_sent_times:
            return []

        for message in chat_transcript[::-1]:
            if message.author.id != author_id_for_chatbot:
                last_message_time = datetime.fromtimestamp(message.timestamp)
                break


        if (datetime.now() - last_message_time).total_seconds() > self.silence_time * 60 and self.send_counter < self.max_sent_times:
            self.send_counter += 1

            sentence = "Looks like you've reached a discussion block. Here are a few suggestions to proceed!"

            return [{"message": Message(author=Author(author_id_for_chatbot, "DiscussionBlock"),
                                                    timestamp=-1, text=str(sentence))}]

        return []