
def sb(self, input):
    "Shows what's been said in the channel recently"
    
    if not input.sender.startswith("#"):
        self.say("No scrollback available for PMs")
        return
    
    try:
        lines = int(input.args.strip() if input.args else "10")
    except ValueError:
        lines = 10
    
    if lines > 100:
        lines = 100
    
    for line in self.bot.logger._scrollback(input.sender, lines):
        self.notice(input.nick, line)

sb.rule = ["sb","scrollback"]
sb.usage = [("Get the last n lines that were sent to the channel", "$pcmd <n>")]
sb.example = [("Get the last 30 lines from the current channel", "$pcmd 30"),
    ("Get the default (10) number of recent lines", "$pcmd")]