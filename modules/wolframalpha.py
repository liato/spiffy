import re
import urllib2

from BeautifulSoup import BeautifulSoup as bs

def texttable(plaintext):
    if plaintext.find("\n") == -1:
        return plaintext
    
    copyfloppy = plaintext
    header = False
    firstrow = plaintext[:plaintext.find("\n")]
    
    if "|" not in firstrow:
        header = True
        plaintext = plaintext[plaintext.find("\n")+1:]
    
    table = [[f.strip() for f in e.split("|")] for e in plaintext.split("\n")]

    try:
        lens = [max(len(row[col]) for row in table)+2 for col in range(len(table[0]))]
    except IndexError:
        return copyfloppy
    
    ret = []
    if header:
        ret.append(center(firstrow,sum(lens) + len(table[0])-1))
    ret.extend("|".join(center(e,lens[i]) for i,e in enumerate(row)) for row in table)
    return "\n".join(ret)

def unic(match):
    return unichr(int(match.group(1), 16))

def isposint(s):
    try:
        s = int(s)
        if s < 0:
            return False
    except (ValueError, TypeError):
        return False
    return True

def center(s, l):
    """Center a string s in a space of l characters.
       center("foo",5) -> " foo " and so on"""
    d = l-len(s)
    a,b = divmod(d,2)
    return "%s%s%s" % (a*" ", s, (a+b)*" ")

def wolframalpha(self, input):
    """Query wolframalpha.com for information about anything."""
    baseurl = "http://www88.wolframalpha.com/input/"
    cmd = input.args or ""

    parser = self.OptionParser()
    parser.add_option("-d", "-r", "--results", dest="results", default="4")
    (options, args) = parser.parse_args(cmd.split())

    if not args:
        raise self.BadInputError("A query is required.")

    if not (options.results.lower() in ('a', 'all') or isposint(options.results)):
        raise self.BadInputError("Invalid results argument, should be 'all' or numeric.")
    
    query = " ".join(args)
    results = options.results

    data = urllib2.urlopen(baseurl+"?i="+urllib2.quote(query.encode('utf-8'))+"&asynchronous=pod&equal=Submit").read()
    recalcUrl = re.search("'(recalculate.jsp\?id=[^']*?)'", data, re.I)
    if recalcUrl:
        recalcdata = urllib2.urlopen(baseurl+recalcUrl.group(1)).read()
    else:
        recalcdata = ""
    podUrls = re.findall("'(pod.jsp\?id=[^']*?)'", data+recalcdata, re.I)
    if podUrls:
        for url in podUrls:
            try:
                data=data+str(urllib2.urlopen(baseurl+str(url)).read())
            except urllib2.HTTPError:
                pass
    data = bs(data, convertEntities=bs.HTML_ENTITIES)
    pods = data.findAll('div', { "class": ["pod ", "pod "] })
    if results.startswith("a"):
        results = len(pods)
    else:
        results = int(results)
    
    for i, pod in enumerate(pods):
        if i > results-1:
            break
        title = pod.find('h1').span.contents[0]
        text = pod.find('img')['alt']
        unicodr = re.compile(r"\\\\:([a-fA-F0-9]{4,8})")
        text = unicodr.sub(unic, text)
        text = text.replace("\\n","\n").replace("\\'s","'s")
        text = re.split(r'\n{2,}',text)
        output = []
        for p in text:
            p = re.sub(r'(?im)(\n|^)\([^\n]+\)($|\n)', '', p)
            p = re.sub(r'^\n+', '', p)
            p = re.sub(r'\n+$', '', p)
            if p:
                output.append(texttable(p))

        if output:
            self.say("\x02"+title)
            for j, l in enumerate(output):
                lines = l.split("\n")
                for n in lines:
                    self.say(n)
                if i < results-1:
                    self.say("\x02")


wolframalpha.rule = ["wa", "wolframalpha"]
wolframalpha.usage = [("Query wolframalpha for information about anything", "$pcmd <query>"),
    ("Display <num> number of 'pods' for the given query", "$pcmd -d <num> <query>"),
    ("Display all 'pods' for the given query", "$pcmd -d all <query>")]
wolframalpha.example = [("Query wolframalpha for information about New York", "$pcmd New York"),
    ("Query wolframalpha for information about IBM and Apple and show the first 3 'pods'", "$pcmd -d 3 IBM Apple"),
    ("Query wolframalpha for information about Cryptonite and show all 'pods'", "$pcmd -d all Cryptonite")]
