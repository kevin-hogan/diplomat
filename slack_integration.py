import sys
import getopt
from chat_service_to_bot_integrator import ChatServiceToBotIntegrator
from typing import List
from chatbot import Message, Author
from slack_sdk import WebClient


class SlackToBotIntegrator(ChatServiceToBotIntegrator):
    def __init__(self, path_to_config, slack_web_client, channel_id, bot_user_id):
        super().__init__(path_to_config, chatbot_author_id=bot_user_id)
        self.slack_web_client = slack_web_client
        self.channel_id = channel_id

    def request_transcript_and_convert_to_message_list(self) -> List[Message]:
        response = client.conversations_history(channel=self.channel_id)
        messages = [Message(Author(m["user"], m["user"]), m["ts"], m["text"])
                    for m in response.data["messages"] if "user" in m.keys()]
        messages.reverse()
        return messages

    def post_chatbot_interventions(self, interventions: List[Message]) -> None:
        for i in interventions:
            client.chat_postMessage(channel=self.channel_id, text=i.text)


if __name__ == "__main__":
    argv = sys.argv[1:]
    opts, _ = getopt.getopt(argv, "p:t:c:b:")
    if len(opts) != 4:
        print("slack_integration.py -p <path_to_config> -t <slack-bot-token> -c <channel-id> -b <bot-user-id>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-p":
            path_to_config = arg
        elif opt == "-t":
            slack_bot_token = arg
        elif opt == "-c":
            channel_id = arg
        elif opt == "-b":
            bot_user_id = arg

    client = WebClient(token=slack_bot_token)
    SBI = SlackToBotIntegrator(path_to_config, client, channel_id, bot_user_id)
    SBI.seconds_per_poll = 10
    SBI.start()

    
    