import sys
import getopt
from integrator.chat_service_to_bot_integrator import ChatServiceToBotIntegrator
from typing import List, Dict, Union, Any
from chatbot import Message, Author
from slack_sdk import WebClient


class SlackToBotIntegrator(ChatServiceToBotIntegrator):
    def __init__(self, path_to_config: str, slack_web_client: WebClient, channel_id: str,
                 bot_user_id: int, dynamic_configuration: bool, observers_list: List = None):
        super().__init__(path_to_config, chatbot_author_id=bot_user_id, dynamic_configuration=dynamic_configuration,
                         observers_list=observers_list)
        self.slack_web_client = slack_web_client
        self.channel_id = channel_id
        self.members = self.get_channel_members()

    def get_channel_members(self) -> List:
        response = self.slack_web_client.conversations_members(channel=channel_id)
        members = [member for member in response.data["members"] if member != self.chatbot_author_id and member
                   not in self.observers_list]
        # print(members, self.chatbot_author_id)
        return members

    def request_transcript_and_convert_to_message_list(self) -> List[Message]:
        try:
            response = self.slack_web_client.conversations_history(channel=self.channel_id)
        except Exception as e:
            print(e.__str__())
            return []

        messages = [Message(Author(m["user"], m["user"]), m["ts"], m["text"])
                    for m in response.data["messages"] if "user" in m.keys() and m["user"] not in self.observers_list]
        messages.reverse()
        return messages

    def post_chatbot_interventions(self, interventions: List[Dict[str, Union[Message, Any]]]) -> None:
        for m_dict in interventions:
            i = m_dict["message"]

            if m_dict.get("ephemeral", False) is False:
                i = m_dict["message"]

                if i.blocks is not None:
                    self.slack_web_client.chat_postMessage(channel=self.channel_id, blocks=i.blocks)
                else:
                    self.slack_web_client.chat_postMessage(channel=self.channel_id, text=i.text)
            else:
                i = m_dict["message"]
                self.slack_web_client.chat_postEphemeral(channel=self.channel_id, text=i.text, user=m_dict["author_id"])


if __name__ == "__main__":
    argv = sys.argv[1:]
    opts, _ = getopt.getopt(argv, "p:t:c:b:d:o")

    if len(opts) != 4 and len(opts) != 5 and len(opts) != 6:
        print("slack_integration.py -p <path_to_config> -t <slack-bot-token> -c <channel-id> -b <bot-user-id> "
              "[-d <dynamic-configuration>]")
        sys.exit(2)

    dynamic_config = False
    slack_bot_token = None
    channel_id = None
    bot_user_id = None
    path_to_config = None
    observers_list = ["U01P0CLLCDP", "U01V6CFTJ3D"]

    for opt, arg in opts:
        if opt == "-p":
            path_to_config = arg
        elif opt == "-t":
            slack_bot_token = arg
        elif opt == "-c":
            channel_id = arg
        elif opt == "-b":
            bot_user_id = arg
        elif opt == "-d":
            dynamic_config = arg

    client = WebClient(token=slack_bot_token)
    SBI = SlackToBotIntegrator(path_to_config, client, channel_id, bot_user_id, dynamic_config, observers_list)
    SBI.seconds_per_poll = 10
    SBI.start()
