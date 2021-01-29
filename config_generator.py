from typing import List
import json

class ConfigGenerator:
    def __init__(self):
        self.transcript = None
        self.done = False
        self._config = {
            "DiversityPlugin": {
            "EphemeralMessages": True,
            "CheckPastTill": 10,
            "DiversityCheckList": [
                {"WordList": ["Guys", "Gals", "Ladies", "Gals"], "Substitutes":  "People, Folks, Teammates"},
                {"WordList": ["Handicapped", "Disabled"], "Substitutes": "People with disabilities"},
                {"WordList": ["Dwarf", "Midget"], "Substitutes": "Person of short stature"},
                {"WordList": ["Females"], "Substitutes": "Women"},
                {"WordList": ["Master", "Slave", "Master/Slave"], "Substitutes": "Primary/Replica, Primary/Standby"},
                {"WordList": ["Blacklist", "Whitelist", "Blacklist/Whitelist"], "Substitutes": "Allowlist, Blocklist"},
                {"WordList": ["Man hours", "Manhours", "Manpower"], "Substitutes": "Workforce, Team, Personnel"},
                {"WordList": ["Chairman", "Foreman"], "Substitutes":  "Chairperson, Chair, Moderator, Discussion Leader"}
            ],
            "WarningPhrase": "Please consider using more inclusive terms like {} instead of {}"
            },

            "OverspeakingPlugin": {
                "MessageWindow": 5,
                "MessageCountThreshold": 3,
                "WarningFormatString": "{0} is overspeaking!"
            }
        }

        self.config = {}
        self.questions = ["Choose which plugin do you want to use? (OverspeakingPlugin / DiversityPlugin)"]
        self.chosen_plugin = None

    def _get_choice(self):

        for question in self.questions:
            yield question
        self.done = True

    def update_config(self, question, text):
        if len(self.config) == 0:
            self.config = {text: {}}
            s = list(self._config[text].keys())
            self.questions.extend(s)
            self.chosen_plugin = text
            return

        try:
            text = json.loads(text)
        except:
            pass
        self.config[self.chosen_plugin][question] = text

    def get_config(self):
        return self.config

    def is_done(self):
        return self.done