import re
import urllib

from utils import decodehtml, removehtml

def cleanup(s):
    s = re.sub(r'\<br ?\/?\>', chr(10), s)
    s = re.sub(r'</?b>', chr(2), s)
    s = decodehtml(s)
    s = re.sub(r'<[^>]+>', '', s)
    return s
    
def urbandictionary(self, input):
    """Look up a word in the urban dictionary"""

    parser = self.OptionParser()
    parser.add_option('-d', '-r', '--display', '--results', dest="results", type="int", default=1)
    options, args = parser.parse_args((input.args or "").split())
    args = ' '.join(args)
    
    if options.results > 10:
        options.results = 10
    elif options.results < 1:
        options.results = 1
    
    what = args.encode('utf-8')

    try:
        url = 'http://www.urbandictionary.com/define.php?term=%s' % urllib.quote(what)
        data = urllib.urlopen(url).read()
    except IOError: 
        self.say('Error: Unable to establish a connection to urbandictionary.com')
        return

    data = data.replace(chr(10),'').replace(chr(13),'')
    data = re.sub("<!--.+?-->","",data)

    m = re.findall(r"<td class='index'>.*?</td>.*?<td class='word'>(?P<word>.*?)</td>.*?definition'>(?P<def>.*?)</div>.*?<div class='example'>(?P<ex>.*?)</div>",data,re.IGNORECASE)
    if m:
        if len(m) < options.results:
            options.results = len(m)
        self.say('\x02%s:' % m[0][0])
        for x in range(options.results):
            if options.results > 1:
                header = '[\x02%s\x02] \x1fDefinition\x1f: ' % str(x+1)
            else:
                header = '\x1fDefinition\x1f: '
            for y in cleanup(m[x][1]).split(chr(10)):
                if y.strip():
                    self.say(header+y.strip())
                if options.results > 1:
                    header = '\x02 \x02               '
                else:
                    header = '            '

            if options.results > 1:
                header = '\x02 \x02   \x1fExample\x1f:    '
            else:
                header = '\x1fExample\x1f:    '
            for y in cleanup(m[x][2]).split(chr(10)):
                if y.strip():
                    self.say(header+y.strip())
                if options.results > 1:
                    header = '\x02 \x02               '
                else:
                    header = '            '

    else:
        self.say('Your search for \x02%s\x02 did not return any results.' % args)

urbandictionary.rule = ["ud", "urbdic", "urbandictionary"]
urbandictionary.usage = [('Look up word in the urban dictionary', '$pcmd <word>'),
                ('Display num definitions for the word', '$pcmd -d<num> <word>')]
urbandictionary.example = [('Look up the word \'tinfoil hat\'', '$pcmd tinfoil hat'),
                            ('Display the top 3 definitions for the word \'kebab\'', '$pcmd -d3 kebab')]

