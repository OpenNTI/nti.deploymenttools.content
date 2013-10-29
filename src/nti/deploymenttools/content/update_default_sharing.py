#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import set_default_root_sharing

import argparse
import ConfigParser
import os

def update_default_sharing(config):
        # Scan the library and identify content packages
        content_library = []
        filelist = os.listdir(config['content-library'])
        for file in filelist:
            file = os.path.join(config['content-library'], file)
            if os.path.isdir(file):
                if os.path.exists(os.path.join(file, '.version')):
                    content_library.append(file)

        # Set / reset the default sharing for each content package
        for content in content_library:
            print( "Setting default root sharing on %s for environment '%s' (if applicable)." % (os.path.basename(content), config['environment']) )
            set_default_root_sharing( content, config['environment'])

DEFAULT_CONFIG_FILE='~/etc/nti_util_conf.ini'

def _parse_args():
    # Parse command line args
    arg_parser = argparse.ArgumentParser( description="Content Updater" )
    arg_parser.add_argument( '-c', '--config', default=DEFAULT_CONFIG_FILE,
                             help="Configuration file. The default is: %s" % DEFAULT_CONFIG_FILE )
    arg_parser.add_argument( '-l', '--content-library', dest='content_library', default='', 
                             help="Path from which the content is served from" )
    arg_parser.add_argument( '--environment', default='', 
                             help="Defines which environment settings to use. Valid choices are 'alpha' and 'prod'." )
    return arg_parser.parse_args()

def main():
    args = _parse_args()

    # Read the config file
    configfile = ConfigParser.SafeConfigParser()
    configfile.read( os.path.expanduser( args.config ) )

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}
    config['environment'] = args.environment or configfile.get('deployment', 'environment')
    config['content-library'] = args.content_library or configfile.get('local', 'content-library')

    update_default_sharing(config)

if __name__ == '__main__': # pragma: no cover
        main()
