import urllib2
import re
from utils import decodehtml

def spotifytrack(url):
    data = urllib2.urlopen(url).read()

    regex = r'<a id="title" href[^>]+>([^<]+)</a>.+<div class="artist">.+?title="([^"]+?)"'

    m = re.search(regex,data,re.I | re.DOTALL)
    b = chr(2)
    ret = "%sSpotify track:%s %s - %s" % (b,b,m.group(2),m.group(1))
    return ret

def spotifyalbum(url):
    data = urllib2.urlopen(url).read()

    regex = r'<a id="title" href[^>]+>([^<]+)</a>.+<div class="artist">.+?title="([^"]+?)"'

    m = re.search(regex,data,re.I | re.DOTALL)
    b = chr(2)
    ret = "%sSpotify album:%s %s - %s" % (b,b,m.group(2),m.group(1))
    return ret

def spotify(self, input):
    """Automatically catches Spotify URLs and retrieves track info"""
    
    trackreg = r"(http://open.spotify.com/track/[^\s]+)"
    track = re.search(trackreg,input.args,re.I)

    if track:
        self.say(decodehtml(spotifytrack(track.group(1))))
        return

    albumreg = r"(http://open.spotify.com/album/[^\s]+)"
    album = re.search(albumreg,input.args,re.I)
    
    if album:
        self.say(decodehtml(spotifyalbum(album.group(1))))
        return
    
    # TODO: playlists?
    playlist = None
    if playlist:
        pass
    # http://open.spotify.com/user/mechmut/playlist/34p0Dzx0M3fuBSKP0LuBqp

spotify.rule = r".*http://open.spotify.com/.+"
