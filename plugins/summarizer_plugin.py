from chatbot import FeaturePlugin, Message, Author
from rake_nltk import Rake
from typing import Dict, Any, Union, List
from datetime import datetime, timedelta


class SummarizerPlugin(FeaturePlugin):
    def __init__(self, config: dict):
        self.config = config
        self.rake = Rake()

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        if not chat_transcript[-1].text.startswith("/summarize days="):
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
