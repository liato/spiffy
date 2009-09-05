def help(self, input):
    """Displays information, usage and examples for a given command."""

    cmd = input.args
    if not cmd:
        raise self.BadInputError()
    if cmd in self.aliases:
        cmd = self.aliases[cmd]
        for e in self.doc[cmd]:
            if e:
                self.say(e)
    else:
        self.say("Sorry, can't help you with %s." % cmd)
    
help.rule = ["help"]
help.usage = [("Get help for a command", "$pcmd <command>")]
help.example = [("Get help for the help command", "$pcmd help")]

def commands(self, input):
    """Displays a list of all available commands."""
    self.say('\x02Available commands:')
    cmds = self.doc.keys()
    cmds.sort()
    for cmd in self.split(', '.join(cmds)):
        self.say('  ' + cmd)
    self.say("Use %shelp <command> to get more information about a command." % self.config.get('prefix',''))
commands.rule = ['commands']
commands.usage = [("List all available commands", "$pcmd")]
   