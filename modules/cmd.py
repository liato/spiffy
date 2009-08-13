def cmd(self, input):
    """Admin-only command, runs the supplied argument as Python code within the bot itself."""

    if input.isowner():
        cmd = input.groups()[1]
        
        try:
            msg = chr(2) + "Result: " + chr(2) + str(eval(cmd))
        except Exception, e:
            msg = chr(2) + "Exception raised: " + chr(2) + str(e)

        self.say(msg)

cmd.rule = (["cmd"], "(.+)")
cmd.usage = [("Run <command> and display the result","$pcmd <command>")]
cmd.example = [("Send a raw line of text to the IRC server","$pcmd self.sendLine('<data to send>')")]

