import operator
import urllib2

def codeslice(self, input):
    """Show one or more slices of a textfile on the Internet"""
    if not input.args:
        raise self.BadInputError()

    slices, url = input.args.split('http', 1)

    if not slices or not url:
        raise self.BadInputError()
    
    slices = slices.strip().split(',')
    url = "http"+url.strip()

    try:
        data = urllib2.urlopen(url)
        if not data.headers.dict.get("content-type","").startswith("text/"):
            self.say("Error: The target url has to be of type: text/*")
            return
        
        data = data.read()

    except urllib2.HTTPError, e:
        self.say("Error: Could not get the source. (%s)" % e)
        return

    data = data.split("\n")
    for i, slice in enumerate(slices):
        i = i+1
        slice = slice.strip()
        if len(slice) > 0:
            try:
                if ":" in slice:
                    start, end = [int(s) if s else None for s in slice.split(":", 1)]
                    if start > 0:
                        start = start-1
                    lines = data[start:end]
                else:
                    slice = int(slice)
                    if slice > 0:
                        slice = slice-1
                    lines = [data[slice]]
                    
                if len(lines) > 20:
                    self.say("\x02Code from slice #%s:\x02 (Showing the first 20 of %s lines)" % (i, len(lines)))
                    lines = lines[0:20]
                elif len(lines) == 0:
                    self.say("\x02Slice #%s is empty" % (i,))
                    continue
                else:
                    self.say("\x02Code from slice #%s:" % (i,))
                for line in lines:
                    if line:
                        self.say(line)
                    else:
                        self.say("\x02") #Send an "blank" line.
                    
            except Exception, e:
                print e
                self.say("Error: Invalid slice?. (%s)" % slice)

codeslice.rule = ["cs", "codeslice"]
codeslice.usage = [("Get slices of text from an URL. Slices here work (almost) the same way slices work on lists in python and are separated by ','", "$pcmd <slice>[,<slice>[...]] <url>")]
codeslice.example = [("Display the first to the tenth line from the file at http://docs.python.org/_sources/whatsnew/2.6.txt", "$pcmd 1:10 http://docs.python.org/_sources/whatsnew/2.6.txt"),
    ("Display all the lines from the file at http://docs.python.org/_sources/copyright.txt", "$pcmd : http://docs.python.org/_sources/copyright.txt"),
    ("Display line 10 to 20, 40 to 45 and line 82 from the file at http://docs.python.org/_sources/tutorial/introduction.txt", "$pcmd 10:20,40:45,82 http://docs.python.org/_sources/tutorial/introduction.txt"),
    ("Display the last 10 lines from thee file at http://docs.python.org/_sources/library/constants.txt", "$pcmd -10: http://docs.python.org/_sources/library/constants.txt")]
