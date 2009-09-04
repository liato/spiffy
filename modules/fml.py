#!/usr/bin/env python

from xml.dom import minidom
import re, urllib

def fml(self, input): 
   """Fetches a random entry from FMyLife.com."""

   xmldoc = minidom.parse(urllib.urlopen("http://api.betacie.com/view/random?key=readonly&language=en"))
   xmllist = xmldoc.getElementsByTagName("text")
   self.say(xmllist[0].childNodes[0].data)
      
fml.commands = ['fml']
fml.usage = [("Fetch a random entry", "$pcmd")]
fml.thread = True
