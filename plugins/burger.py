import feedparser
import time

def burger(self,input):
    """Burger of the day!"""

    post = feedparser.parse("https://www.facebook.com/feeds/page.php?format=rss20&id=530367483660523").entries[0]

    if post.published.startswith(time.strftime("%a, %d %b %Y")):
        self.say(post.description)
    else:
        self.say("No burger for today!")
    

burger.rule = ["burger"]
burger.usage = [("Show today's burger",
              "$pcmd")]

