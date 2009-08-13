def help(self,input):
    """Displays information, usage and examples for a given command."""

    cmd = input.groups()[1]
    if cmd in self.doc:
        for e in self.doc[cmd]:
            if e:
                self.say(e)
    
help.rule = (["help"], "(.+)")
help.usage = [("Get help for a command", "$pcmd <command>")]
help.example = [("Get help for the help command", "$pcmd help")]
