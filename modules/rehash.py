def rehash(self, input): 
    """Reloads the configuration for the current network, for use by admins only.""" 
    if not input.isowner():
        self.say('This command is for admins only.')
        return

    s = lambda x: '' if len(x) == 1 else 's'

    if input.group(2) == '-v':
        verbose = True
    else:
        verbose = False

    
    info = self.bot.rehash()
    if info == False:
        self.say('Error: Unable to rehash, config.py is missing.')
        return
    
    if verbose:
        if info['settings']['added']:
            self.say('Added \x02%s\x02 new setting%s:' % (len(info['settings']['added']), s(info['settings']['added'])))
            for setting in info['settings']['added']:
                self.say(" + '%s': %s" % setting)

        if info['settings']['removed']:
            self.say('Removed \x02%s\x02 setting%s:' % (len(info['settings']['removed']), s(info['settings']['removed'])))
            for setting in info['settings']['removed']:
                self.say(" - '%s'" % setting)

        if info['settings']['changed']:
            self.say('Changed \x02%s\x02 setting%s:' % (len(info['settings']['changed']), s(info['settings']['changed'])))
            for setting in info['settings']['changed']:
                self.say(" * '%s': %s \x02->\x02 %s" % setting)
        
        if info['modules']['added']:
            self.say('Loaded \x02%s\x02 new module%s:' % (len(info['modules']['added']), s(info['modules']['added'])))
            self.say(", ".join(info['modules']['added']))

        if info['modules']['removed']:
            self.say('Removed \x02%s\x02 module%s:' % (len(info['modules']['removed']), s(info['modules']['removed'])))
            self.say(", ".join(info['modules']['removed']))    

    self.say('Configuration successfully reloaded!')
        
rehash.rule = ('$nick', ['rehash'], r'(\S+)?')
rehash.usage = [("Reload the configuration and all modules", "$nick $cmd"),
    ("Verbose version of the command above", "$nick $cmd -v")]
