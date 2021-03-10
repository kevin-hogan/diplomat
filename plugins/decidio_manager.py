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

        self.default_routes = config["default_routes"]
        self.notify_before = config["notify_before"]

        self.meetings = []
        self.event_start_time = None
        self.notified = False
        self.cum_times = {}
        self.author_id = None

    def authenticate(self):
        json = {"username": self.username, "password": self.password}
        response = requests.post(self.url + "/login/", json=json)
        return response.json()["access_token"]

    def put_json_synchronous(self, uri, json_payload, access_token):
        headers = {"Authorization": "Bearer " + access_token}
        return requests.put(self.url + uri, headers=headers, json=json_payload)

    def get_json_synchronous(self, uri, access_token):
        headers = {"Authorization": "Bearer " + access_token}
        return requests.get(self.url + uri, headers=headers)

    @staticmethod
    def _compose_message(message, author_id_for_chatbot) -> List[Dict[str, Union[Message, Any]]]:
        return [{"message": Message(author=Author(author_id_for_chatbot, "TimeManagement"), timestamp=-1, text=message)}]

    @staticmethod
    def _add_markdown_section(text: str):
        return {"type": "section", "text": {"type": "mrkdwn", "text": text}}

    def reset(self):
        self.start_spotted = False
        self.meeting_times_received = False
        self.event_id = None
        self.meetings = []
        self.event_start_time = None
        self.cum_times = {}

    def get_results(self, last_message, author_id):
        m_id = [i for i in last_message if i.isdigit()]
        payload = {"meeting_id": int("".join(m_id)), "topk": self.config["topk"]}
        results = requests.get(self.config["results_url"], params=payload).json().get("rankings", [])

        if len(results) == 0:
            return self._compose_message("No results to show for meeting with id: {}".format(m_id),
                                         author_id)
        message = "\n-------------------------------------------------------------\n".join(results)
        return self._compose_message(message, author_id)

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        # This can become a separate plugin!
        if chat_transcript[-1].text.startswith("/diplomat show meeting results="):
            last_message = chat_transcript[-1].text
            return self.get_results(last_message, author_id_for_chatbot)

        self.author_id = author_id_for_chatbot

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
                self.reset()
                return self._compose_message("DecidioManager: The credentials in the config do not match.",
                                             author_id_for_chatbot)

            data = self.get_json_synchronous("/v1/events/{}".format(self.event_id), access_token)

            if data.status_code != 200:
                self.reset()
                event_id = self.event_id
                return self._compose_message("DecidioManager: Event with id: {} does not exist".format(event_id),
                                             author_id_for_chatbot)

            if "diplomat" not in [x["name"] for x in data.json().get("participants", [])]:
                self.reset()
                return self._compose_message("Decidio Manager: Diplomat not added to the event. "
                                             "Please add diplomat and try again. ", author_id_for_chatbot)

            # Signal start of the meeting
            blocks = list()
            blocks.append("*Diplomat will help you manage the following event*")

            event_name = data.json().get("name", "")
            creator = data.json().get("creator", {}).get("name", "")

            meetings = data.json().get("meetings", [])
            # Only take the scheduled meetings
            self.meetings = [meeting for meeting in meetings if meeting.get("status", None) == "SCHEDULED"]

            if len(self.meetings) == 0:
                self.reset()
                return self._compose_message("There are no scheduled meetings in this event.", author_id_for_chatbot)

            blocks.append("*Event Name:* {}".format(event_name))
            blocks.append("*Created By:* {}".format(creator))

            blocks.append("This event has the following meetings: ")

            for meeting in self.meetings:
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

                cum_times = [times[0]]

                for time in times[1:]:
                    cum_times.append(time + cum_times[-1])

                for id, meeting in enumerate(self.meetings):
                    self.cum_times[meeting.get("id")] = cum_times[id]

            except:
                return self._compose_message("DecidioManager: Time values should be integers. Please try again.",
                                             author_id_for_chatbot)

            self.meeting_times_received = True
            self.event_start_time = datetime.now()

            return self._compose_message("DecidioManager: Diplomat will start the event soon.", author_id_for_chatbot)

        if self.event_start_time is None:
            return []

        cur_time = datetime.now()
        time_elapsed = (cur_time - self.event_start_time).total_seconds() // 60

        try:
            meetings = self.get_meeting_info()
        except:
            return self._compose_message("Error occurred while trying to get information related to the meeting",
                                         author_id_for_chatbot)

        meetings = [meeting for meeting in meetings if meeting.get("status") != "COMPLETED"]

        if len(meetings) == 0:
            event_id = self.event_id
            self.reset()

            message = "DecidioManager: The event (id={}) has ended.\n".format(event_id)
            message += "You can use the command `/diplomat show meeting results=<meeting_id>` to see the results of your meeting.\n"

            return self._compose_message(message, author_id_for_chatbot)

        # Check if there are any meetings that are to be stopped or to be notified!
        in_progress = False

        for meeting in meetings:
            if meeting.get("status") != "IN_PROGRESS":
                continue

            # Time has elapsed!
            if self.cum_times[meeting["id"]] <= time_elapsed:
                return self.stop_meeting(meeting)

            # Send notification.
            if self.cum_times[meeting["id"]] - time_elapsed <= 2:
                return self.notify(meeting)

            in_progress = True

        # Check if there are meetings to be started.
        if in_progress:
            return []

        # Start the first scheduled meeting
        for meeting in self.meetings:
            if meeting.get("status") == "SCHEDULED":
                return self.start_meeting(meeting)

        return []

    def get_meeting_info(self):
        access_token = self.authenticate()
        data = self.get_json_synchronous("/v1/events/{}".format(self.event_id), access_token)
        return data.json()["meetings"]

    def _control_meeting(self, meeting, status):
        meeting_uri = self.default_routes.get(meeting.get("meetingType", None), None)

        if meeting_uri is None:
            return self._compose_message("Meeting type {} is not supported".format(meeting.get("meetingType", None)),
                                         self.author_id)

        uri = "/v1/{}/{}".format(meeting_uri, meeting.get("id"))
        access_token = self.authenticate()
        meeting["status"] = status

        response = self.put_json_synchronous(uri, meeting, access_token)

        if response.status_code == 200:
            self.notified = False
            return self._compose_message("Meeting *{}* is {}.".format(meeting["name"], meeting["status"]), self.author_id)

        return self._compose_message("Some error occurred while trying to start meeting *{}*.".format(meeting["name"]),
                                     self.author_id)

    def start_meeting(self, meeting):
        return self._control_meeting(meeting, "IN_PROGRESS")

    def stop_meeting(self, meeting):
        return self._control_meeting(meeting, "COMPLETED")

    def notify(self, meeting):
        if self.notified:
            return []

        self.notified = True
        return self._compose_message("Only {} minutes left for {} meeting to end".format(self.notify_before,
                                                                                         meeting["name"]), self.author_id)