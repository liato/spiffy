import copy
import htmlentitydefs
import re
import urllib2

from BeautifulSoup import BeautifulSoup as bs

# Unescape code by Fredrik Lundh - October 28, 2006
# http://effbot.org/zone/re-sub.htm#unescape-html
def _unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)
    
hexentityMassage = copy.copy(bs.MARKUP_MASSAGE)
hexentityMassage = [(re.compile('&#x([^;]+);'),
                     lambda m: '&#%d' % int(m.group(1), 16))]

class imdblib(object):
    class Movie(object):
        def __init__(self, id, fullplot = False):
            if isinstance(id,int):
                id = str(id)
            m = re.search(r"(?:tt)?(?P<id>\d{7})",id,re.I)
            if m:
                self.id = m.group("id")
            else:
                raise ValueError("Invalid imdb id.")
    
            self.title = None
            self.genres = []
            self.rating = None
            self.votes = None
            self.top = None
            self.directors = []
            self.plot = None
            self.fullplot = None
            self.tagline = None
            self.release = None
            self.runtime = None
            self.countries = []
            self.languages = []
            self.cast = []
            self.year = None
            self.usercomment = None
            self.posterurl = None
            self.fullplot = fullplot
            self.update()
    
    
        def _infodiv(self, movie, text, find=None, **kw):
            try:
                if not find:
                    return movie.find("h5", text=text).parent.parent.contents[2].replace("\n","")
                else:
                    return [str(x.string).replace("\n","") for x in movie.find("h5", text=text).parent.parent.findAll(find, **kw)]
                    
            except:
                if not find:
                    return None
                else:
                    return []
    
    
        def update(self):
            data = urllib2urlopen("http://www.imdb.com/title/tt%s/" % self.id)
            movie = bs(data.read(), convertEntities=bs.HTML_ENTITIES, markupMassage=hexentityMassage)
            self.title = movie.head.title.string
            year = re.search(r"\((?P<year>\d{4})\)$",self.title)
            if year:
                self.year = year.group("year")
                self.title = re.sub(r"\s\(\d{4}\)$","",self.title)
            
            try:
                self.directors = [d.string for d in movie.find(id="director-info").findAll("a")]
            except:
                self.directors = []
            
            self.directors = []
                
            self.genres = self._infodiv(movie, "Genre:", find="a", href=re.compile("/Sections/"))
            try:
                self.rating = movie.find("div", "general rating").find("div", "meta").b.string
                self.votes = movie.find("div", "general rating").find("div", "meta").a.string
            except:
                self.rating = None
                self.votes = "No votes"
            
            try:
                self.top = "%s" % movie.find("div", "general rating").find("div", "bottom").div.a.string
            except:
                self.top = None
            self.plot = self._infodiv(movie, "Plot:")
            self.tagline = self._infodiv(movie, "Tagline:")
            self.release = self._infodiv(movie, "Release Date:")
            self.usercomment = self._infodiv(movie, "User Comments:")
            self.runtime = self._infodiv(movie, "Runtime:")
            self.countries = self._infodiv(movie, "Country:", find="a")
            self.languages = self._infodiv(movie, "Language:", find="a")
            self.cast = []
            for n in movie.find("table", "cast").findAll("tr"):
                try:
                    id = dict(n.contents[1].a.attrs).get("href","")
                    m = re.search(r"(?P<id>nm\d{7})",id)
                    if m:
                        id = m.group("id")
                    else:
                        id = "nm0000000"
                    try:
                        name = n.contents[1].a.string
                    except AttributeError:
                        name = n.contents[1].string
    
                    try:                    
                        cname = n.contents[3]
                        cname = repr(cname)
                        cname = cname.decode('utf8') #cname.decode(movie.originalEncoding)
                        cname = re.sub(r"<[^>]+>", u"", cname)
                    except:
                        cname = ""
                        
                    self.cast.append((id, name, cname))
                except Exception:
                    pass
            
            try:
                self.posterurl = dict(movie.find("div","photo").a.img.attrs)["src"]
                if "title_noposter" in self.posterurl:
                    self.posterurl = None
            except (TypeError, KeyError):
                pass
    
            if self.fullplot:            
                data = urllib2urlopen("http://www.imdb.com/title/tt%s/plotsummary" % self.id)
                movie = bs(data.read(), convertEntities=bs.HTML_ENTITIES, markupMassage=hexentityMassage)
                try:
                    self.fullplot = movie.find(id="tn15content").find("p","plotpar").contents[0].strip()
                except AttributeError:
                    pass
    
    
    class Name:
        def __init__(self, id):
            if isinstance(id,int):
                id = str(id)
            m = re.search(r"(?:nm)?(?P<id>\d{7})",id,re.I)
            if m:
                self.id = m.group("id")
            else:
                raise ValueError("Invalid imdb id.")
    
            self.name = None
            self.birthdate = None
            self.birthplace = None
            self.deathdate = None
            self.biography = None
            self.trivia = None
            self.awards = None
            self.altnames = None
            self.filmography = []
            self.photourl = None
            self.update()
    
    
        def _infodiv(self, movie, text, find=None, **kw):
            try:
                if not find:
                    return movie.find("h5", text=text).parent.parent.contents[2].replace("\n","")
                else:
                    return [str(x.string).replace("\n","") for x in movie.find("h5", text=text).parent.parent.findAll(find, **kw)]
                    
            except:
                if not find:
                    return None
                else:
                    return []
    
    
        def update(self):
            data = urllib2urlopen("http://www.imdb.com/name/nm%s/" % self.id)
            movie = bs(data.read(), convertEntities=bs.HTML_ENTITIES, markupMassage=hexentityMassage)
            self.name = movie.head.title.string
            self.birthdate = " ".join(self._infodiv(movie,"Date of Birth:", find="a", href=re.compile(r"onthisday|borninyear", re.I)))
            self.birthplace = "".join(self._infodiv(movie,"Date of Birth:", find="a", href=re.compile(r"bornwhere", re.I)))
            self.deathdate = " ".join(self._infodiv(movie,"Date of Death:", find="a", href=re.compile(r"onthisday|diedinyear", re.I)))
            self.biography = self._infodiv(movie,"Mini Biography:")
            self.trivia = self._infodiv(movie,"Trivia:")
            self.awards = self._infodiv(movie,"Awards:")
            if self.awards:
                self.awards = re.sub(r"\s+", " ", self.awards.strip())
            self.altnames = self._infodiv(movie,"Alternate Names:")
     
            self.filmography = []
            for x in movie.findAll("div", "filmo"):
                try:
                    title = x.find("h5").a.string.replace(":","")
                except Exception:
                    title = ""
                for n in x.find("ol").findAll("li"):
                    n = repr(n)
                    n = n.decode('utf8')
                    m = re.search(r'<a[^>]*href="/title/(?P<id>tt\d{7})/"[^>]*>(?P<name>[^<]*?)</a>.*\)', n, re.I)
                    if m:
                        self.filmography.append((m.group("name"), title))
            
            try:
                self.photourl = dict(movie.find("div","photo").a.img.attrs)["src"]
                if "nophoto" in self.photourl:
                    self.photourl = None
            except TypeError,KeyError:
                pass
    
    
    class Search:
        def __init__(self, string, name=False):
            self.searchstring = string
            self.result = None
            self.name = name
            self.update()
    
        def update(self, searchstring = None):
            if not searchstring:
                searchstring = self.searchstring
            else:
                self.searchstring = searchstring
           
            m = re.search(r"(?P<result>(?:nm|tt)\d{7})", searchstring, re.I)
            if m:
                self.result = m.group("result")
                return
            
            if self.name:
                regex = [r"<a href=\"\/name\/(nm\d{7})\/\"[^>]*>([^<]*?)</a>"]
                url = "http://www.imdb.com/find?s=nm&q=%s" % urllib2quote(searchstring.encode('latin-1'))
            else:
                m = re.search(r"(?P<movie>.+?)(?: \(?(?P<year>\d{4})\)?)?$", searchstring, re.I)
                movie = m.group("movie").strip(" ")
                year = m.group("year")
                movie = re.escape(movie)
        
                regex = []
                if year:
                   year = re.escape(year)
                   regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>("+movie+")</a> \("+year+"\)")
                   regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>("+movie+", The)</a> \("+year+"\)")
                   regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>(\""+movie+"\")</a> \("+year+"\)")
                   regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>([^<]*?"+movie+"[^<]*?)</a> \("+year+"\)")
                   regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>([^<]*?)</a> \("+year+"\)")
                regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>("+movie+")</a>")
                regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>("+movie+", The)</a>")
                regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>(\""+movie+"\")</a>")
                regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>([^<]*?"+movie+"[^<]*?)</a>")
                regex.append(r"<a href=\"\/title\/(tt\d{7})\/\"[^>]*>([^<]*?)</a>")
                url = "http://www.imdb.com/find?s=tt&q=%s" % urllib2quote(m.group("movie").encode('latin-1'))
            
        
            url = urllib2urlopen(url)
            if "/find?s=" not in url.url: # We've been redirected to the first result
                m = re.search(r"/(?:name|title)/(?P<result>(?:nm|tt)\d{7})", url.url, re.I)
                if m:
                    self.result = m.group("result")
                    return
                
            #data = _unescape(url.read())
            data = url.read()
    
            self.result = None
            for x in regex:
                m = re.search(x, data, re.IGNORECASE)
                if m:
                    self.result = m.group(1)
                    break

def imdb(self, input):
    """Get information about a movie, tv show or actor."""
    cmd = input.args
    
    parser = self.OptionParser()
    parser.add_option("-r", "--rating", dest="rating", action="store_true", default=False)
    parser.add_option("-R", "--RATING", dest="rating_url", action="store_true", default=False)
    parser.add_option("-n", "-p", "--name", "--person", dest="person", action="store_true", default=False)
    (options, args) = parser.parse_args(cmd.split())

    if not args:
        raise self.BadInputError("A query is required.")
    
    query = " ".join(args)
    if options.person:
        try:
            id = imdblib.Search(query, name=True).result
            if id:
                name = imdblib.Name(id)
            else:
                self.say("Your search for \x02%s\x02 did not return any results." % query)
                return
        except urllib2.HTTPError:
            self.say("Your search for \x02%s\x02 did not return any results." % query)
            return
        except IOError:
            self.say("Error: A connection to IMDB could not be established.")
            
        self.say("\x02%s\x02 - [ \x1f%s\x1f ]" % (name.name, "http://www.imdb.com/name/nm"+name.id))
        if name.birthdate or name.birthplace:
            self.say("\x02Born:\x02 %s" % (name.birthdate or "")+(name.birthplace and " in "+name.birthplace))
        if name.deathdate: self.say("\x02Died:\x02 %s" % name.deathdate)
        if name.biography: self.say("\x02Biography:\x02 %s" % name.biography)
        if name.trivia: self.say("\x02Trivia:\x02 %s" % name.trivia)
        if name.awards: self.say("\x02Awards:\x02 %s" % name.awards)
        if name.altnames: self.say("\x02Alternative names:\x02 %s" % name.altnames)
        if name.filmography: self.say("\x02Filmography:\x02 %s" % ", ".join([x+" ("+y+")" for x, y in name.filmography[:5]]))

    else:
        if options.rating or options.rating_url:
            queries = query.split(",")
        else:
            queries = [query]
        for query in queries:
            query = query.strip()
            try:
                id = imdblib.Search(query)
                if id.result:
                    movie = imdblib.Movie(id.result)
                else:
                    self.say("Your search for \x02%s\x02 did not return any results." % query)
                    return
            except urllib2.HTTPError:
                self.say("Your search for \x02%s\x02 did not return any results." % query)
                return
            except IOError:
                self.say("Error: A connection to IMDB could not be established.")
            

            if options.rating_url:
                if movie.rating:
                    self.say("\x02%s%s\x02:  %s (%s) %s - [ \x1f%s\x1f ]" % (movie.title, movie.year and " ("+str(movie.year)+")" or "", movie.rating, movie.votes, movie.top and "["+movie.top+"]" or "", "http://www.imdb.com/title/tt"+movie.id))
                else:
                    self.say("\x02%s%s\x02 is not yet rated. - [ \x1f%s\x1f ]" % (movie.title, movie.year and " ("+str(movie.year)+")" or "", "http://www.imdb.com/title/tt"+movie.id))


            elif options.rating:
                if movie.rating:
                    self.say("\x02%s%s\x02:  %s (%s) %s" % (movie.title, movie.year and " ("+str(movie.year)+")" or "", movie.rating, movie.votes, movie.top and "["+movie.top+"]" or ""))
                else:
                    self.say("\x02%s%s\x02 is not yet rated." % (movie.title, movie.year and " ("+str(movie.year)+")" or "",))


            else:
                self.say("\x02%s%s\x02 - [ \x1f%s\x1f ]" % (movie.title, movie.year and " ("+str(movie.year)+")" or "", "http://www.imdb.com/title/tt"+movie.id))
                if movie.directors: self.say("\x02Director:\x02 %s" % ", ".join(movie.directors))
                if movie.genres: self.say("\x02Genre:\x02 %s" % ", ".join(movie.genres))
                if movie.rating: self.say("\x02Rating:\x02 %s (%s) %s" % (movie.rating, movie.votes, movie.top and "["+movie.top+"]" or ""))
                if movie.plot: self.say("\x02Plot:\x02 %s" % movie.plot)
                if movie.tagline: self.say("\x02Tagline:\x02 %s" % movie.tagline)
                if movie.release: self.say("\x02Release:\x02 %s" % movie.release)
                if movie.runtime: self.say("\x02Runtime:\x02 %s" % movie.runtime)
                if movie.countries: self.say("\x02Country:\x02 %s" % ", ".join(movie.countries))
                if movie.languages: self.say("\x02Language:\x02 %s" % ", ".join(movie.languages))
                if movie.usercomment: self.say("\x02User comments:\x02 %s" % movie.usercomment)
                if movie.cast: self.say("\x02Cast:\x02 %s" % ", ".join([name+" as "+cname for id, name, cname in movie.cast[:5]]))

imdb.rule = ["mdb", "imdb"]
imdb.usage = [("Display information about a movie or tv show", "$pcmd <title>"),
    ("Display information about an actor", "$pcmd -p <name>"),
    ("Only show the title and rating for a list of movies", "$pcmd -r <title>[, <title>[, <title>...]]")]
imdb.example = [("Display information about the movie V for Vendetta", "$pcmd V for Vendetta"),
    ("Display information about the actor Rob McElhenney", "$pcmd -p Rob McElhenney"),
    ("Show the title and rating for the first three terminator movies", "$pcmd -r The Terminator, Terminator 2: Judgment Day, Terminator 3: Rise of the Machines")]