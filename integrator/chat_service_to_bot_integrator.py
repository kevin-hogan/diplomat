import abc
import time
import inspect
from plugins import feature_plugins
from typing import List, Dict
from chatbot import Message, generate_interventions, Author
from datetime import datetime
from config_generator import ConfigGenerator


class ChatServiceToBotIntegrator(metaclass=abc.ABCMeta):
    def __init__(self, path_to_config: str, seconds_per_poll: float = 10, chatbot_author_id: int = -1):
        self.path_to_config = path_to_config
        self.seconds_per_poll = seconds_per_poll
        self.chatbot_author_id = chatbot_author_id

    @abc.abstractmethod
    def request_transcript_and_convert_to_message_list(self) -> List[Message]:
        pass

    @abc.abstractmethod
    def post_chatbot_interventions(self, interventions: Dict) -> None:
        pass

    def filter_transcript(self, chat):
        cur_time = datetime.now()
        time_diff = (cur_time - datetime.fromtimestamp(chat.timestamp)).total_seconds()
        # Only consider messages posted in the last "check_past_till" seconds
        if time_diff > 5:
            return True

        if chat.author.id == self.chatbot_author_id:
            return True

        return False

    def start(self):

        # Config Generator: Look for start
        start_finder = False

        while not start_finder:
            transcript = self.request_transcript_and_convert_to_message_list()
            for chat in transcript:
                # Skip messages posted by the chatbot!
                if self.filter_transcript(chat):
                    continue

                if chat.text == "/start diplomat":
                    start_finder = True
                    break

            time.sleep(3)

        m = Message(text="Initializing the Diversity Bot", author=Author(self.chatbot_author_id, "DiversityBot"),
                    timestamp=-1)
        self.post_chatbot_interventions([{"message": m, "ephemeral": False}])

        c = ConfigGenerator()

        for question in c._get_choice():
            q = "Enter the value for: {}".format(question)
            m = Message(text=q,
                        author=Author(self.chatbot_author_id, "DiversityBot"),
                        timestamp=-1)
            self.post_chatbot_interventions([{"message": m, "ephemeral": False}])

            received_answer = False
            while not received_answer:
                transcript = self.request_transcript_and_convert_to_message_list()

                for chat in transcript:
                    if self.filter_transcript(chat):
                        continue
                    else:
                        print("Question: {}, Answer: {}".format(question, chat.text))
                        c.update_config(question, chat.text)
                        received_answer = True

                time.sleep(5)

        conf_dict = c.get_config()
        print(conf_dict)

        m = Message(text="Launching plugin {}".format(list(conf_dict.keys())[0]),
                    author=Author(self.chatbot_author_id, "DiversityBot"),
                    timestamp=-1)

        self.post_chatbot_interventions([{"message": m, "ephemeral": False}])

        feature_plugin_classes = [member for member in inspect.getmembers(feature_plugins, inspect.isclass)
                                if member[1].__module__ == "plugins.feature_plugins" and member[0] in conf_dict.keys()]

        plugins = [fpc[1](conf_dict[fpc[0]]) for fpc in feature_plugin_classes]

        while True:
            transcript = self.request_transcript_and_convert_to_message_list()
            chatbot_messages = generate_interventions(plugins, transcript, self.chatbot_author_id)
            self.post_chatbot_interventions(chatbot_messages)
            time.sleep(self.seconds_per_poll)