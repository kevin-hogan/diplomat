from datetime import datetime
from chatbot import FeaturePlugin, Message, Author
from typing import Dict, Any, Union, List
from json import loads

import requests
import re


class DecidioManager(FeaturePlugin):
    def __init__(self, config: dict):
        self.config = config
        self.start_spotted = False
        self.meeting_times_received = False
        self.event_id = None
        self.username = config["username"]
        self.url = config["url"]
        self.password = config["password"]
        self.meetings = None

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

    @staticmethod
    def _add_markdown_section(text: str):
        return {"type": "section", "text": {"type": "mrkdwn", "text": text}}

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        if not chat_transcript[-1].text.startswith("/diplomat manage event=") and not self.start_spotted and \
                not self.meeting_times_received:
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

            # Mark start
            self.start_spotted = True

            # Signal start of the meeting
            blocks = list()
            blocks.append("*Diplomat will help you manage the following event*")

            event_name = data.json().get("name", "")
            creator = data.json().get("creator", {}).get("name", "")

            meetings = data.json().get("meetings", [])

            if len(meetings) == 0:
                return self._compose_message("No meetings added to this event.", author_id_for_chatbot)

            self.meetings = meetings
            blocks.append("*Event Name:* {}".format(event_name))
            blocks.append("*Created By:* {}".format(creator))

            blocks.append("This event has the following meetings: ")

            for meeting in meetings:
                blocks.append("{} ({}) -> id={}".format(meeting["name"], meeting["meetingType"], meeting["id"]))

            blocks.append("Please let me know how many minutes do you want each meeting to run.")
            blocks.append('Respond in the format: `/diplomat assign times [time1, time2...]`. '
                          'time1, time2 are times in minutes in the same order for meetings listed above.')

            blocks = [self._add_markdown_section(x) for x in blocks]

            return [{"message": Message(author=Author(author_id_for_chatbot, "DecidioManager"), timestamp=-1,
                                        blocks=blocks, text="")}]

        # Event has been verified and diplomat is helping manage the event.
        if self.start_spotted and chat_transcript[-1].text.startswith("/diplomat assign times") and not \
                self.meeting_times_received:

            message = chat_transcript[-1].text
            try:
                times = re.findall(r'\[.*?\]', message)[0]
                times = loads(times)
            except:
                return self._compose_message("DecidioManager: Please check the format!", author_id_for_chatbot)

            if len(times) != len(self.meetings):
                return self._compose_message("DecidioManager: Number of times passed don't match the number of meetings! "
                                             "Please try again.",
                                             author_id_for_chatbot)
            try:
                for id, time in enumerate(times):
                    self.meetings[id]["timer"] = int(time)
            except:
                return self._compose_message("DecidioManager: Time values should be integers. Please try again.", author_id_for_chatbot)

            self.meeting_times_received = True


        
        return []