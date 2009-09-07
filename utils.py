import re

def decodehtml(s):
    """Decode HTML entities in the given text."""
    entity_sub = re.compile(r'&(#(\d+|x[\da-fA-F]+)|[\w.:-]+);?').sub

    def uchr(c):
        if not isinstance(c, int):
            return c
        if c>255: return unichr(c)
        return chr(c)

    def decode_entity(match):
        what = match.group(1)
        if what.startswith('#x'):
            what = int(what[2:], 16)
        elif what.startswith('#'):
            what = int(what[1:])
        else:
            from htmlentitydefs import name2codepoint
            what = name2codepoint.get(what, match.group(0))
        return uchr(what)

    return entity_sub(decode_entity, s)


def unescapeuni(s):
    """Converts \uXXXX in s to their ascii counterparts"""
    ret = ""
    i = 0
    while i < len(s):
        if s[i:i+2] == "\u":
            x = int(s[i+2:i+6],16)
            if x < 256:
                ret += chr(x)
            i += 6
        else:
            ret += s[i]
            i+=1
    return ret


def removehtml(s):
    """Remove html tags"""
    s = re.sub("<[^>]+>", "", s)
    s = re.sub(" +", " ", s)
    return s

def humantime(seconds, string=True):
    """Given seconds return a human readable time"""
    m,s = divmod(seconds, 60)
    h,m = divmod(m, 60)
    d,h = divmod(h, 24)
    w,d = divmod(d, 7)
    if string:
        return ((w and str(w)+'w ' or '')+(d and str(d)+'d ' or '')+(h and str(h)+'h ' or '')+(m and str(m)+'m ' or '')+(s and str(s)+'s' or '')).strip()
    else:
        return (w, d, h, m, s)
