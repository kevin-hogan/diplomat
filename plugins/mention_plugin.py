from datetime import datetime
from chatbot import FeaturePlugin, Message, Author
from typing import Dict, Any, Union, List
from random import choice

import math


class MentionPlugin(FeaturePlugin):

    def __init__(self, config: dict):
        self.config = config

        self.mention_list = [x.lower() for x in config["mention_list"].keys()]
        self.mention_explanations = config["mention_list"]

        self.notify_times = config["notify_times"]
        self.mention_counter = {}

        self.warning_format_strings = config["WarningFormatStrings"]
        self.start_time = None
        self.last_processed = None
        self.mention_spotted = False
        self.total_time = None
        self.last_notification = None

    @staticmethod
    def _compose_message(message, author_id_for_chatbot) -> List[Dict[str, Union[Message, Any]]]:
        return [
            {"message": Message(author=Author(author_id_for_chatbot, "MentionPlugin"), timestamp=-1, text=message)}]

    def cleanup(self):
        self.start_time = None
        self.mention_counter = {}
        self.last_processed = None
        self.mention_spotted = False
        self.total_time = None
        self.last_notification = None

    def notify(self):
        phrase = choice(self.warning_format_strings)
        alerts = []

        for word, explanations in self.mention_explanations.items():
            word = word.lower()
            if self.mention_counter.get(word) is None:
                alerts.append(explanations)
                continue

            # Alert if for more than half the time, the term was not found
            mention_time_elapsed = (self.mention_counter.get(word) - self.start_time).total_seconds()
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            if elapsed_time - mention_time_elapsed > ((self.total_time * 60) / 2):
                alerts.append(explanations)

        return phrase.format(", ".join(alerts))

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        if not chat_transcript[-1].text.startswith("/activate mention_plugin time=") and not self.mention_spotted:
            return []

        if chat_transcript[-1].text.startswith("/activate mention_plugin time="):
            last_message = chat_transcript[-1].text
            timeline = [i for i in last_message if i.isdigit()]
            self.total_time = int("".join(timeline))
            self.mention_spotted = True
            self.start_time = datetime.now()
            self.last_processed = chat_transcript[-1].timestamp
            # Signal start of the meeting
            return self._compose_message("MentionPlugin: Plugin activated for {} minutes".format(self.total_time),
                                         author_id_for_chatbot)

        cur_time = datetime.now()

        if (cur_time - self.start_time).total_seconds() / 60 > self.total_time:
            # Signify end of meeting
            message = "MentionPlugin: Plugin deactivated.".format(self.total_time)
            self.cleanup()
            return self._compose_message(message, author_id_for_chatbot)

        unprocessed_list = []
        for elem in chat_transcript[::-1]:
            if elem.author.id == author_id_for_chatbot:
                continue

            if elem.timestamp <= self.last_processed:
                break
            unprocessed_list.append(elem)

        if unprocessed_list:
            self.last_processed = unprocessed_list[0].timestamp

        for elem in unprocessed_list:
            words = elem.text.split()
            for word in words:
                word = word.lower()
                if word in self.mention_list:
                    if self.mention_counter.get(word) is None:
                        self.mention_counter[word] = datetime.fromtimestamp(elem.timestamp)
                    self.mention_counter[word] = max(self.mention_counter[word], datetime.fromtimestamp(elem.timestamp))

        time_elapsed = int((cur_time - self.start_time).total_seconds() // 60)

        if time_elapsed < 1:
            return []

        notify_minutes = int(self.total_time // (self.notify_times + 1))

        if time_elapsed % notify_minutes != 0:
            return []

        print(self.mention_counter)
        if not self.last_notification:
            self.last_notification = cur_time
            message = self.notify()
            return self._compose_message(message, author_id_for_chatbot)

        if (cur_time - self.last_notification).total_seconds() < 60:
            return []

        message = self.notify()
        self.last_notification = cur_time
        return self._compose_message(message, author_id_for_chatbot)
