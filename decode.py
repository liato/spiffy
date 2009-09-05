# This pattern matches a character entity reference (a decimal numeric
# references, a hexadecimal numeric reference, or a named reference).
import re
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

def htmldecode(text):
    "Decode HTML entities in the given text."
    return entity_sub(decode_entity, text)
