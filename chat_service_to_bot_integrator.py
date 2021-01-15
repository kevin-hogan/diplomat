import abc
import time
import inspect
import json
import system_plugin_functions
from typing import List
from chatbot import Message, generate_chatbot_messages

class ChatServiceToBotIntegrator(metaclass=abc.ABCMeta):
    def __init__(self, path_to_config: str, seconds_per_poll: float = 1, chatbot_author_id: int = -1):
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
        system_plugin_classes = [member for member in inspect.getmembers(system_plugin_functions, inspect.isclass)
                                if member[1].__module__ == "system_plugin_functions" and member[0] in conf_dict.keys()]
        system_plugins = [spc[1](conf_dict[spc[0]]) for spc in system_plugin_classes]

        while True:
            transcript = self.request_transcript_and_convert_to_message_list()
            chatbot_messages = generate_chatbot_messages(system_plugins, transcript, self.chatbot_author_id)
            self.post_chatbot_interventions(chatbot_messages)
            time.sleep(self.seconds_per_poll)