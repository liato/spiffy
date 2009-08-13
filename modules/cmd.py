import re, subprocess

def cmd(self, input):
    """Admin-only command, runs the supplied argument as Python code within the bot itself.
Usage: !cmd <command>
Example: !cmd self.userlist["#spiffy"]"""
    if input.isowner():
        cmd = input.groups()[1]
        
        try:
            msg = chr(2) + "Result: " + chr(2) + str(eval(cmd))
        except Exception, e:
            msg = chr(2) + "Exception raised: " + chr(2) + str(e)

        self.say(msg)

cmd.rule = (["cmd"], "(.+)")

