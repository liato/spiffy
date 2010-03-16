import re
import urllib

from utils import removehtml, decodehtml

def unnecessaryknowledge(self, input):
    """Get som unnecessary knowledge from unnecessaryknowledge.com"""

    if not input.args:
        raise self.BadInputError()
        
    try:
        data = urllib.urlopen('http://www.unnecessaryknowledge.com/_default.asp').read()
    except IOError: 
        self.say("Error: Unable to establish a connection to unnecessaryknowledge.com.")
        return

    data = data.replace('\r','').replace('\n','')
    m = re.search(r"<h2[^>]+?>(?P<text>.+?)</h2>",data,re.IGNORECASE)
    if not m:
        self.say("Error: Unable to parse data.")
        return

    msg = m.group("text")
    re.sub(r"(?:<a href[^>]*>|</a>)",'\x02', msg)
    msg = decodehtml(msg).strip()
    self.say(msg)

unnecessaryknowledge.rule = ["uk", "unnecessaryknowledge"]
unnecessaryknowledge.usage = [('Get a random entry', '$pcmd')]