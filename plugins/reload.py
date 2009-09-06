import re
import os
import sys
import time

def reload(self, input): 
    """Reloads a plugin, for use by admins only.""" 
    if not input.isowner():
        self.say('This command is for admins only.')
        return

    name = input.args
    if (not name) or (name == '*'): 
        self.loadPlugins()
        self.say('All plugins reloaded.')
        return

    try:
        plugin = self.loadPlugin(os.path.join('plugins', name + '.py'))
    except (IOError, ImportError), e:
        self.say('\x02Error:\x02 %s' % e)
        return

    if hasattr(plugin, '__file__'): 
        mtime = os.path.getmtime(plugin.__file__)
        modified = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mtime))
    else:
        modified = 'unknown'
    self.reply('<plugin%s (version: %s)' % (repr(plugin)[7:], modified))

reload.rule = ['reload']
reload.usage = [("Reload a plugin from the plugins directory", "$pcmd <plugin>"),
    ("Reload all plugins from the plugins directory", "$pcmd *")]
reload.example = [("Reload the imdb plugin","$pcmd imdb")]
