from datetime import datetime
from chatbot import FeaturePlugin, Message, Author
from typing import Dict, Any, Union, List

import requests


class DecidioManager(FeaturePlugin):
    def __init__(self, config: dict):
        self.config = config
        self.start_spotted = False
        self.event_id = None
        self.username = config["username"]
        self.url = config["url"]
        self.password = config["password"]

    def authenticate(self):
        json = {"username": self.username, "password": self.password}
        response = requests.post(self.url + "/login/", json=json)
        return response.json()["access_token"]

    def get_json_synchronous(self, uri, access_token):
        headers = {"Authorization": "Bearer " + access_token}
        return requests.get(self.url + uri, headers=headers)

    @staticmethod
    def _compose_message(message, author_id_for_chatbot) -> List[Dict[str, Union[Message, Any]]]:
        return [{"message": Message(author=Author(author_id_for_chatbot, "TimeManagement"), timestamp=-1, text=message)}]

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        if not chat_transcript[-1].text.startswith("/diplomat manage event=") and not self.start_spotted:
            return []

        if chat_transcript[-1].text.startswith("/diplomat manage event=") and not self.start_spotted:

            last_message = chat_transcript[-1].text
            e_id = [i for i in last_message if i.isdigit()]
            self.event_id = int("".join(e_id))
            self.start_spotted = True

            try:
                access_token = self.authenticate()

            except Exception as e:
                return self._compose_message("DecidioManager: The credentials in the config do not match.",
                                             author_id_for_chatbot)

            data = self.get_json_synchronous("/v1/events/{}".format(self.event_id), access_token)

            if data.status_code != 200:
                return self._compose_message("DecidioManager: Event with id: {} does not exist".format(self.event_id),
                                             author_id_for_chatbot)

            if "diplomat" not in [x["name"] for x in data.json().get("participants", [])]:
                return self._compose_message("Decidio Manager: Diplomat not added to the event. "
                                             "Please add diplomat and try again. ", author_id_for_chatbot)

            self.start_spotted = True
            # Signal start of the meeting
            return self._compose_message("DecidioManager: Diplomat will help you "
                                         "manage your event with id: {}".format(self.event_id),
                                         author_id_for_chatbot)

        # Event has been verified and diplomat is helping manage the event.

        return []