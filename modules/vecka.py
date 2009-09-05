import datetime
import re
import time

days = ["",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"]

def vecka(self, input):
    """Displays the week and weekday for today or for a given date."""
    m = input.args
    msg = lambda s: self.say(s)

    if m:
        m = re.match(r"(\d{2,4}?)-(\d{1,2})-(\d{1,2})", m)
        if not m:
            raise self.BadInputError()
            return
        t = map(int, m.groups())
        if t[0] < 100:
            t[0] += 2000
        date = datetime.date(t[0], t[1], t[2])
    else:
        t = time.localtime()
        date = datetime.date(t[0], t[1], t[2])
        
    msg("%s is a %s in week %s%d%s" % (str(date),
                                       days[date.isoweekday()],
                                       chr(2),date.isocalendar()[1],chr(2)))


vecka.rule = ["vecka", "week"]
vecka.usage = [("Display the current week", "$pcmd"),
               ("Display the week for a given date", "$pcmd YYYY-MM-DD")]
vecka.example = [("Display the week Halloween was in in 1999", "$pcmd 1999-10-31")]
