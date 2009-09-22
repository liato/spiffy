import random
import re

greetings = ["hi","hey","yo","sup","zup","hello","ey","eyy", "what up"]
addons = ["sup?", "what's the happy hap?", "what's new?", "how's it hangin'?"]
endings = [" :D", "!", "...", " lol!"]

def hi(self, input):
    cmd = input.args
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
        return
    
    if re.match("(?:thx|tack|thanks),? " + self.nickname, cmd, re.I):
        self.reply("np")
        return
    
    m = re.match(self.nickname + r"[:!,] (\^5|_5|-5).*", cmd, re.I)
    if m:
        self.reply(m.group(1) + "!")

hi.rule = r".*"
