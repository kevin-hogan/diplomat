from chatbot import FeaturePlugin, Message, Author
from typing import Dict, Any, Union, List
from datetime import datetime


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

    @staticmethod
    def apply_operation(a, b, op):
        if op == "-":
            return a-b

        if op == "+":
            return a + b

        if op == "*":
            return a * b

        if op == "%" and b !=0:
            return a % b

        if op == "/" and b != 0:
            return int(a / b)

    def generate_interventions(self, chat_transcript: List[Message], author_id_for_chatbot: int,
                               channel_members: List) -> List[Dict[str, Union[Message, Any]]]:

        if not chat_transcript[-1].text.startswith("/start discussion time=") and not self.start_spotted:
            return []

        if chat_transcript[-1].text.startswith("/start discussion time="):
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

        if (cur_time - self.start_time).total_seconds() / 60 > self.total_time:
            # Signify end of meeting
            message = "TimerPlugin: Your {} minute discussion timer has ended.".format(self.total_time)
            self.start_spotted = False
            self.last_notification = None
            self.total_time = None
            return self._compose_message(message, author_id_for_chatbot)

        if (cur_time - self.last_notification).total_seconds() // 60 == 0:
            # Skip the initial minute right after the notification is sent.
            return []

        time_left = self.total_time - (cur_time - self.start_time).total_seconds() // 60
        elapsed = (cur_time - self.start_time).total_seconds() // 60

        if not self.config.get("EnableCustomNotifications", False):
            return []

        for notif in self.config.get("CustomNotifications", []):
            if notif.get("parameter", "time_left") == "elapsed":
                pass_value = elapsed
            else:
                pass_value = time_left

            output = self.apply_operation(pass_value, notif["value"], notif["op"])

            if output == 0:
                self.last_notification = cur_time
                return self._compose_message(notif.get("message", "TimerPlugin: You have {} minutes left").format(time_left),
                                             author_id_for_chatbot)
        #
        # if ((cur_time - self.last_notification).total_seconds() // 60) % self.config["NotifyEvery"] == 0:
        #     # Notify!
        #     self.last_notification = cur_time
        #     return self._compose_message("TimerPlugin: You have {} minutes left".format(time_left),
        #                                  author_id_for_chatbot)
        return []
