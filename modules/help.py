def help(self,input):
    """Displays information, usage and examples for a given command."""

    cmd = input.group(2)
    if not cmd:
        raise self.BadInputError()
    if cmd in self.doc:
        for e in self.doc[cmd]:
            if e:
                self.say(e)
    else:
        self.say("Sorry, can't help you with %s." % cmd)
    
help.rule = (["help"], "(.+)")
help.usage = [("Get help for a command", "$pcmd <command>")]
help.example = [("Get help for the help command", "$pcmd help")]
