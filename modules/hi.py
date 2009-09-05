import re
import random

greetings = ["hi","hey","yo","sup","zup","hello","ey","eyy", "what up"]
addons = ["sup?", "what's the happy hap?", "what's new?", "how's it hangin'?"]
endings = [" :D", "!", "...", " lol!"]

def hi(self, input):
    cmd = input.group()
    greetreg = "(?:" + "|".join(greetings) + ")"

    # something like "<nick>, zup?"
    a = re.match(self.nickname + "[,!:] ?" + greetreg + "[!?]*", cmd, re.I)

    # something like "yo <nick>!"
    b = re.match(greetreg + " " + self.nickname + ".*", cmd, re.I)

    if a or b:
        if random.randint(0,1):
            # we add an addon too
            self.say(random.choice(greetings) + " " + input.nick + ", " + random.choice(addons))
        else:
            # no addon for you!
            self.say(random.choice(greetings) + " " + input.nick + random.choice(endings))

hi.rule = r".*"
