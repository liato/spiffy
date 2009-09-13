import re
import urllib
from xml.dom import minidom

def reddit(self, input): 
    """Get the top submission from reddit.com"""

    parser = self.OptionParser()
    parser.add_option('-d', '-r', '--display', '--results', dest="results", type="int")
    options, args = parser.parse_args((input.args or "").split())
    
    if options.results > 10:
        options.results = 10
    elif options.results < 1:
        options.results = 1

    xmldoc = minidom.parse(urllib.urlopen("http://www.reddit.com/.rss"))
    xmllist = xmldoc.getElementsByTagName("item")
    gen = ((e.childNodes[0].childNodes[0].data,e.childNodes[1].childNodes[0].data) for e in xmllist)
    
    for i in range(options.results):
        e = gen.next()
        self.say('\x02%s\x02 [ %s ]' % (e[0], e[1]))

      
reddit.rule = ['reddit']
reddit.usage = [('Display the top submission', '$pcmd'),
                ('Display the top num submissions', '$pcmd -d<num>')]
reddit.example = [('Display the top 5 submissions', '$pcmd -d5')]