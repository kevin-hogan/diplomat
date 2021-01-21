import abc
from typing import List


class Author():
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name

    def __repr__(self):
        return f"Author(id={repr(self.id)}, name={repr(self.name)})"


class Message:
    def __init__(self, author: Author, timestamp: float, text: str):
        self.author = author
        self.timestamp = float(timestamp)
        self.text = text

    def __eq__(self, other):
        return self.author == other.author and self.timestamp == other.timestamp and self.text == other.text
    
    def __repr__(self):
        return f"Message(author={repr(self.author)}, timestamp={repr(self.timestamp)}, text={repr(self.text)})"


class FeaturePlugin(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, config: dict):
        pass

    @abc.abstractmethod
    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int) -> List[Message]:
       pass


def generate_interventions(plugins: FeaturePlugin, chat_transcript: List[Message], author_id_for_chatbot: int) -> List[Message]:
    messages = []
    for p in plugins:
        messages += p.generate_interventions(chat_transcript, author_id_for_chatbot)
    
    return messages
