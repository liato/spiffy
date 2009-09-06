import re
import urllib
from xml.dom import minidom

def fml(self, input): 
   """Fetches a random entry from FMyLife.com."""

   xmldoc = minidom.parse(urllib.urlopen("http://api.betacie.com/view/random?key=readonly&language=en"))
   xmllist = xmldoc.getElementsByTagName("text")
   self.say(xmllist[0].childNodes[0].data)
      
fml.rule = ['fml']
fml.usage = [("Fetch a random entry", "$pcmd")]
