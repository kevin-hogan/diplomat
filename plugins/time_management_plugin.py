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
        self.notify_times = {}

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

        if op == ">" and a > b:
            return 0

        if op == "<" and a < b:
            return 0

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
            self.notify_times = {}

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

        last_message_at_time = None
        for message in chat_transcript[::-1]:
            if message.author.id != author_id_for_chatbot:
                last_message_at_time = datetime.fromtimestamp(chat_transcript[-1].timestamp)
                break

        time_since_last_message = (cur_time - last_message_at_time).total_seconds()

        if not self.config.get("EnableCustomNotifications", False):
            return []

        for notif in self.config.get("CustomNotifications", []):
            to_evaluate = notif.get("parameter", "time_left")

            if to_evaluate == "elapsed":
                pass_value = elapsed

            elif to_evaluate == "time_since_last_message":
                pass_value = time_since_last_message

            else:
                pass_value = time_left

            output = self.apply_operation(pass_value, notif["value"] * 60, notif["op"])

            if output != 0:
                continue

            if notif.get("max_times") is not None and notif.get("max_times") <= self.notify_times.get(to_evaluate, 0):
                continue

            self.notify_times[to_evaluate] = self.notify_times.get(to_evaluate, 0) + 1
            self.last_notification = cur_time
            return self._compose_message(notif.get("message", "TimerPlugin: You have {} minutes left").format(time_left),
                                         author_id_for_chatbot)
        return []
