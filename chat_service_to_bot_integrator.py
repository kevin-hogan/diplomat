import abc
import time
import inspect
import json
import feature_plugins
from typing import List
from chatbot import Message, generate_interventions


class ChatServiceToBotIntegrator(metaclass=abc.ABCMeta):
    def __init__(self, path_to_config: str, seconds_per_poll: float = 10, chatbot_author_id: int = -1):
        self.path_to_config = path_to_config
        self.seconds_per_poll = seconds_per_poll
        self.chatbot_author_id = chatbot_author_id

    @abc.abstractmethod
    def request_transcript_and_convert_to_message_list(self) -> List[Message]:
        pass

    @abc.abstractmethod
    def post_chatbot_interventions(self, interventions: List[Message]) -> None:
        pass

    def start(self):
        with open(self.path_to_config) as f:
            conf_dict = json.load(f)
        feature_plugin_classes = [member for member in inspect.getmembers(feature_plugins, inspect.isclass)
                                if member[1].__module__ == "feature_plugins" and member[0] in conf_dict.keys()]
        plugins = [fpc[1](conf_dict[fpc[0]]) for fpc in feature_plugin_classes]

        while True:
            transcript = self.request_transcript_and_convert_to_message_list()
            chatbot_messages = generate_interventions(plugins, transcript, self.chatbot_author_id)
            self.post_chatbot_interventions(chatbot_messages)
            time.sleep(self.seconds_per_poll)