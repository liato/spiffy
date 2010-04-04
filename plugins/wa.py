import re
import urllib2

from wolframalpha import WolframAlpha

def isposint(s):
    try:
        s = int(s)
        if s < 0:
            return False
    except (ValueError, TypeError):
        return False
    return True

def wa(self, input):
    """Query wolframalpha.com for information about anything."""
    
    cmd = input.args or ''

    parser = self.OptionParser()
    parser.add_option('-d', '-r', '--results', dest='results', default='4')
    (options, args) = parser.parse_args(cmd.split())

    if not args:
        raise self.BadInputError('A query is required.')

    if not (options.results.lower() in ('a', 'all') or isposint(options.results)):
        raise self.BadInputError("Invalid results argument, should be 'all' or numeric.")
    
    query = ' '.join(args)
    results = options.results

    query = WolframAlpha(query)

    if results.startswith("a"):
        results = len(query.results)
    else:
        results = int(results)
    
    for i, rs in enumerate(query.results[:results]):
        self.say('\x02%s' % rs.title)
        for line in rs.result.split('\n'):
            self.say(line)
        if i+1 < results:
            self.say('\x02')
            

wa.rule = ["wa", "wolframalpha"]
wa.usage = [("Query wolframalpha for information about anything", "$pcmd <query>"),
    ("Display <num> number of 'pods' for the given query", "$pcmd -d <num> <query>"),
    ("Display all 'pods' for the given query", "$pcmd -d all <query>")]
wa.example = [("Query wolframalpha for information about New York", "$pcmd New York"),
    ("Query wolframalpha for information about IBM and Apple and show the first 3 'pods'", "$pcmd -d 3 IBM Apple"),
    ("Query wolframalpha for information about Cryptonite and show all 'pods'", "$pcmd -d all Cryptonite")]
