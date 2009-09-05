import re
import os
import sys
import time

def reload(self, input): 
    """Reloads a module, for use by admins only.""" 
    if not input.isowner():
        self.say('This command is for admins only.')
        return

    name = input.args
    if (not name) or (name == '*'): 
        self.loadModules()
        self.say('All modules reloaded.')
        return

    try:
        module = self.loadModule(os.path.join('modules', name + '.py'))
    except (IOError, ImportError), e:
        self.say('\x02Error:\x02 %s' % e)
        return

    if hasattr(module, '__file__'): 
        mtime = os.path.getmtime(module.__file__)
        modified = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mtime))
    else:
        modified = 'unknown'
    self.reply('%r (version: %s)' % (module, modified))

reload.rule = ['reload']
reload.usage = [("Reload a module from the modules directory", "$nick $cmd <module>"),
    ("Reload all modules from the modules directory", "$nick $cmd *")]
reload.example = [("Reload the imdb module","$nick $cmd imdb")]
