import re
import urllib

from utils import decodehtml, removehtml, unescapeuni


def google(self, input):
    """Perform a web search using the Google search engine"""

    args = input.args or ""
    parser = self.OptionParser()
    parser.add_option("-d", "-r", "--results", dest="results", default=1, type="int")
    (options, args) = parser.parse_args(args.split())
    if not args:
        raise self.BadInputError()
    query = " ".join(args).encode('utf-8')

    if options.results < 1:
        options.results = 1
    elif options.results > 10:
        options.results = 10

    try:
        data = urllib.urlopen('http://www.google.com/uds/GwebSearch?callback=GwebSearch.RawCompletion&context=0&lstkp=0&hl=en&key=ABQIAAAAeBvxXUmueP_8_kTINo0H4hSKL4HoBFFxfS_vfvgFpLqAt5GPWRTHDAESci2RYvZRkcpsYXapXjZWKA&v=1.0&rsz=large&q=%s' % urllib.quote(query)).read()
    except IOError: 
        self.say("Error: Unable to establish a connection to google.com")
        return
    data =  unescapeuni(data)
    data = decodehtml(data)

    m = re.search('estimatedResultCount":"([^"]+)"', data)
    if m:
        matches = m.group(1)
    m = re.findall(r'"url":"([^"]*)".*?"titleNoFormatting":"([^"]*)","content":"([^"]*)"', data, re.IGNORECASE)
    if m:
        if len(m) < options.results:
            options.results = len(m)
        if options.results == 1:
            self.say('\x02%s\x02 - ( \x1f%s\x1f ) [%s matches]' % (removehtml(m[0][1]), urllib.unquote(m[0][0]), matches))
            self.say(removehtml(m[0][2]))
        else:
            self.say('Showing the first \x02%s\x02 of \x02%s\x02 matches' % (options.results, matches))
            for x in range(options.results):
                self.say('\x02%s\x02 - ( \x1f%s\x1f )' % (removehtml(m[x][1]), urllib.unquote(m[x][0])))

    else:
        phenny.say('Your search for \x02%s\x02 did not return any results.' % input.args)

google.rule = ["g","google"]
google.usage = [("Search the World Wide Web using the Google search engine", "$pcmd <query>"),
                ("Display a maximum of num results", "$pcmd -d<num> <query>"),
    ]
google.example = [("Find 'Python' on the World Wide Web", "$pcmd Python"),
                ("Display the first five results for the query above", "$pcmd -d5 Python"),
    ]