#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import gc_catalog

import argparse
import ConfigParser
import os

import logging

logger = logging.getLogger('nti.deploymenttools.content')
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
log_handler.setLevel(logging.INFO)
logger.addHandler(log_handler)

DEFAULT_CONFIG_FILE='~/etc/nti_util_conf.ini'

def _parse_args():
    # Parse command line args
    arg_parser = argparse.ArgumentParser( description="Content Catalog Garbage Collector" )
    arg_parser.add_argument( '-c', '--config', default=DEFAULT_CONFIG_FILE,
                             help="Configuration file. The default is: %s" % DEFAULT_CONFIG_FILE )
    arg_parser.add_argument( '-p', '--contentstore', default='', 
                             help="The directory containing content store" )
    return arg_parser.parse_args()

def main():    
    args = _parse_args()
    content_store = os.path.expanduser(args.contentstore)

    # Read the config file
    configfile = ConfigParser.SafeConfigParser()
    configfile.read( os.path.expanduser( args.config ) )

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}
    config['content-store'] = content_store or configfile.get('local', 'content-store')

    gc_catalog(config['content-store'])


if __name__ == '__main__': # pragma: no cover
        main()
