import inspect
import feature_plugins
from chatbot import generate_interventions, Message, Author

CHATBOT_AUTHOR_ID = -1

def construct_feature_plugins(config):
    feature_plugin_classes = [member for member in inspect.getmembers(feature_plugins, inspect.isclass)
                      if member[1].__module__ == "feature_plugins" and member[0] in config.keys()]
    return [fpc[1](config[fpc[0]]) for fpc in feature_plugin_classes]

def test_empty():
    config = {"OverspeakingPlugin": {"MessageWindow": 5, "MessageCountThreshold": 3, "WarningFormatString": "{0} is overspeaking!"}}
    feature_plugins = construct_feature_plugins(config)

    assert generate_interventions(feature_plugins, [], CHATBOT_AUTHOR_ID) == []

def test_happy_path():
    config = {"OverspeakingPlugin": {"MessageWindow": 5, "MessageCountThreshold": 3, "WarningFormatString": "{0} is overspeaking!"}}
    feature_plugins = construct_feature_plugins(config)

    chat_transcript = [
        Message(Author(1, "Kevin"), 1, "asdf"),
        Message(Author(1, "Kevin"), 2, "qwerty"),
        Message(Author(1, "Kevin"), 3, "zxcv"),
        Message(Author(2, "Tom"), 4, "Hey"),
        Message(Author(3, "Jerry"), 5, "Bye")
    ]
    generated_messages = generate_interventions(feature_plugins, chat_transcript, CHATBOT_AUTHOR_ID)

    assert generated_messages == [Message(Author(CHATBOT_AUTHOR_ID, "Chatbot"), -1, "Kevin is overspeaking!")]

def test_multiple_calls_to_generate():
    config = {"OverspeakingPlugin": {"MessageWindow": 5, "MessageCountThreshold": 3, "WarningFormatString": "{0} is overspeaking!"}}
    feature_plugins = construct_feature_plugins(config)

    chat_transcript = [
        Message(Author(1, "Tom"), 1, "Hey"),
        Message(Author(2, "Jerry"), 2, "Bye"),
        Message(Author(3, "Kevin"), 3, "asdf"),
        Message(Author(3, "Kevin"), 4, "qwerty")
    ]
    generated_messages = generate_interventions(feature_plugins, chat_transcript, CHATBOT_AUTHOR_ID)
    assert generated_messages == []

    chat_transcript += generated_messages
    chat_transcript += [
        Message(Author(3, "Kevin"), 5, "asdf"),
        Message(Author(3, "Kevin"), 6, "qwerty")
    ]
    generated_messages = generate_interventions(feature_plugins, chat_transcript, CHATBOT_AUTHOR_ID)
    assert generated_messages == [Message(Author(CHATBOT_AUTHOR_ID, 'Chatbot'), -1, 'Kevin is overspeaking!')]


def test_overspeaking_count_properly_reset():
    config = {"OverspeakingPlugin": {"MessageWindow": 5, "MessageCountThreshold": 3, "WarningFormatString": "{0} is overspeaking!"}}
    feature_plugins = construct_feature_plugins(config)

    chat_transcript = [
        Message(Author(1, "Tom"), 1, "Hey"),
        Message(Author(2, "Jerry"), 2, "Bye"),
        Message(Author(3, "Kevin"), 3, "asdf"),
        Message(Author(3, "Kevin"), 4, "qwerty"),
        Message(Author(3, "Kevin"), 5, "asdf"),
    ]
    generated_messages = generate_interventions(feature_plugins, chat_transcript, CHATBOT_AUTHOR_ID)
    assert generated_messages == [Message(Author(CHATBOT_AUTHOR_ID, 'Chatbot'), -1, 'Kevin is overspeaking!')]

    chat_transcript += generated_messages
    chat_transcript += [
        Message(Author(3, "Kevin"), 7, "asdf"),
        Message(Author(3, "Kevin"), 8, "qwerty"),
        Message(Author(1, "Tom"), 9, "Hey"),
    ]
    assert generate_interventions(feature_plugins, chat_transcript, CHATBOT_AUTHOR_ID) == []
