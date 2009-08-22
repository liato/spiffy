#!/usr/bin/env python
import sys
import os
import imp

from twisted.internet import reactor
from bot import BotFactory

connections = {}


if __name__ == '__main__':
    if sys.version_info < (2, 5): 
        print >> sys.stderr, 'Error: Requires Python 2.5 or later, from www.python.org'
        sys.exit(1)    

    config_name = os.path.join(sys.path[0], 'config.py')
    if not os.path.isfile(config_name):
        print >> sys.stderr, 'Error: No config(.py) file found.'
        sys.exit(1)

    config = imp.load_source('config', config_name)
    
    if hasattr(config, 'networks'):
        for network in config.networks:
            serverconfig = {}
            config_defaults = {'nick': 'spiffy', 'prefix': r'!',
                               'chandebug': True, 'channels': [],
                                'logevents': ['PRIVMSG', 'JOIN', 'PART',
                                              'MODE', 'TOPIC', 'KICK', 'QUIT',
                                              'NOTICE', 'NICK', '332', '333'],
                                'verbose': True, 'reconnect': 10,
                                'logpath': 'logs'}
            for x in config_defaults:
                serverconfig[x] = config_defaults[x]
            for x in config.__dict__:
                if not x.startswith('__'):
                    serverconfig[x] = config.__dict__[x]
            for x in config.networks[network]:
                serverconfig[x] = config.networks[network][x]
                
            serverconfig['network'] = network

            if 'host' not in serverconfig:
                print 'Error: Could not connect to %s. No host given.' % network
            else:
                print 'Creating connection to %s' % network
                server = serverconfig['host']
                port = 6667
                if isinstance(server, (tuple, list)):
                    server = server[0]
                    serverconfig['activeservernum'] = 0
                else:
                    serverconfig['activeservernum'] = -1
                
                if ':' in server:
                    server, port = server.split(':')
                    port = int(port)

                serverconfig['activeserver'] = (server, port or 6667)
                reactor.connectTCP(server, port or 6667, BotFactory(serverconfig, connections))
        reactor.run()

    else:
        print >> sys.stderr, "Error: No netorks to connect to."
        sys.exit(1)