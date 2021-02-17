from chatbot import FeaturePlugin, Message, Author
from typing import Dict, Any, Union, List
from datetime import datetime

import string


class DiversityPlugin(FeaturePlugin):
    def __init__(self, config: dict):
        self.config = config
        self.check_past_till = config["CheckPastTill"]
        self.diversity_list = config["DiversityCheckList"]
        self.diversity_map = {}
        self.warning_format_string = config["WarningPhrase"]
        self.ephemeral = config["EphemeralMessages"]

        for c in self.diversity_list:
            for w in c["WordList"]:
                self.diversity_map[w.lower()] = c["Substitutes"]

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        cur_time = datetime.now()
        message_list = []

        for chat in chat_transcript:
            # Skip messages posted by the chatbot!

            time_diff = (cur_time - datetime.fromtimestamp(chat.timestamp)).total_seconds()
            # Only consider messages posted in the last "check_past_till" seconds
            if time_diff > self.check_past_till:
                continue

            if chat.author.id == author_id_for_chatbot:
                # print("Found something")
                continue

            message = chat.text.split()
            # print(chat)
            for m in message:
                m = m.translate(str.maketrans('', '', string.punctuation))

                if self.diversity_map.get(m.lower()) is None:
                    continue

                message_list.append(
                    {"message": Message(author=Author(author_id_for_chatbot, "DiversityBot"), timestamp=-1,
                                        text=self.warning_format_string.format(self.diversity_map[m.lower()], m)),
                     "ephemeral": True,
                     "author_id": chat.author.id}
                )

        return message_list
