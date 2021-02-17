from chatbot import FeaturePlugin, Message, Author
from typing import List
from collections import defaultdict, deque
from math import isclose
from datetime import datetime, timedelta
from typing import Dict, Any, Union

from rake_nltk import Rake
import string


class TimeManagementPlugin(FeaturePlugin):
    def __init__(self, config: dict):
        self.config = config
        self.start_spotted = False
        self.last_notification = None
        self.total_time = None
        self.start_time = None

    @staticmethod
    def _compose_message(message, author_id_for_chatbot) -> List[Dict[str, Union[Message, Any]]]:
        return [{"message": Message(author=Author(author_id_for_chatbot, "TimeManagement"), timestamp=-1, text=message)}]

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int) -> \
            List[Dict[str, Union[Message, Any]]]:

        if "/start discussion time=" not in chat_transcript[-1].text and not self.start_spotted:
            return []

        if "/start discussion time=" in chat_transcript[-1].text:
            last_message = chat_transcript[-1].text
            timeline = [i for i in last_message if i.isdigit()]
            self.total_time = int("".join(timeline))
            self.start_spotted = True
            self.last_notification = datetime.now()
            self.start_time = datetime.now()
            # Signal start of the meeting
            return self._compose_message("TimerPlugin: Discussion Timer set for {} minutes".format(self.total_time),
                                         author_id_for_chatbot)

        cur_time = datetime.now()

        if (self.last_notification - self.start_time).total_seconds() // 60 > self.total_time:
            # Signify end of meeting
            message = "TimerPlugin: Your {} minute discussion timer has ended.".format(self.total_time)
            self.start_spotted = False
            self.last_notification = None
            self.total_time = None
            return self._compose_message(message, author_id_for_chatbot)

        if (cur_time - self.last_notification).total_seconds() // 60 == 0:
            # Skip the initial minute right after the notification is sent.
            return []

        if ((cur_time - self.last_notification).total_seconds() // 60) % self.config["NotifyEvery"] == 0:
            # Notify!
            self.last_notification = cur_time
            time_left = self.total_time - (cur_time - self.start_time).total_seconds() // 60
            return self._compose_message("TimerPlugin: You have {} minutes left".format(time_left),
                                         author_id_for_chatbot)
        return []

class SummarizerPlugin(FeaturePlugin):
    def __init__(self, config: dict):
        self.config = config
        self.rake = Rake()

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int) -> \
            List[Dict[str, Union[Message, Any]]]:

        if "/summarize days=" not in chat_transcript[-1].text:
            return []

        if chat_transcript[-1].author.id == author_id_for_chatbot:
            return []

        last_message = chat_transcript[-1].text

        timeline = [i for i in last_message if i.isdigit()]

        td = int("".join(timeline))

        message_list = []

        for chat in chat_transcript:
            if chat.author.id == author_id_for_chatbot:
                continue

            if datetime.fromtimestamp(chat.timestamp) < datetime.now() - timedelta(days=td):
                continue

            message_list.append(chat.text)

        statements = []
        return_messages = []

        self.rake.extract_keywords_from_sentences(message_list)
        for sentence in self.rake.get_ranked_phrases()[:self.config["SummarySize"]]:
            statements.append(sentence)

        for sentence in list(set(statements)):
            return_messages.append({"message": Message(author=Author(author_id_for_chatbot, "Summarizer"),
                                                    timestamp=-1, text=str(sentence))})

        return return_messages


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

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int) -> List[Dict[str, Union[Message, Any]]]:

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


class OverspeakingPlugin(FeaturePlugin):

    def __init__(self, config: dict):
        message_window = int(config["MessageWindow"])
        message_count_threshold = int(config["MessageCountThreshold"])
        if message_window < 1 or message_count_threshold < 1 or message_window < message_count_threshold:
            raise ValueError()
        self.message_window = message_window
        self.message_count_threshold = message_count_threshold
        self.warning_format_string = str(config["WarningFormatString"])

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
            if message.author.id == author_id_for_chatbot: 
                for (author_id, count) in author_id_to_message_count.items():
                    if count >= message_count_threshold:
                        author_id_to_message_count[author_id] = 0
                        author_id_to_accounted_for_ts[author_id] = message.timestamp
            else:
                if len(window) == message_window_size:
                    removed_message = window.popleft()
                    message_accounted_for = removed_message.timestamp < author_id_to_accounted_for_ts[removed_message.author.id]
                    if not message_accounted_for and removed_message.author.id != author_id_for_chatbot:
                        author_id_to_message_count[removed_message.author.id] -= 1
                window.append(message)
                if message.author.id != author_id_for_chatbot:
                    author_id_to_message_count[message.author.id] += 1

        return [author_id_to_author[author_id]
                for author_id, message_count in author_id_to_message_count.items()
                if message_count >= message_count_threshold]

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int) -> List[Dict[str, Union[Message, Any]]]:
        overspeaking_authors = OverspeakingPlugin.get_overspeaking_authors(
            chat_transcript,
            author_id_for_chatbot,
            self.message_window,
            self.message_count_threshold)
        overspeaking_warnings = [{"ephemeral": False, "message": Message(Author(author_id_for_chatbot, "Chatbot"),
                                                                         -1, self.warning_format_string.format(a.name))}
                                 for a in overspeaking_authors]
        
        return overspeaking_warnings
