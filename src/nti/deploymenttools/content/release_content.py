#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import get_content_metadata, symlink_content

import argparse
import ConfigParser
import os

def mark_for_release( config, content ):
    print( 'Marking %s version %s for release.' % ( content['name'], content['version'] ) )
    symlink_content( config, content, 'release' )

DEFAULT_CONFIG_FILE='~/etc/nti_util_conf.ini'

def _parse_args():
    # Parse command line args
    arg_parser = argparse.ArgumentParser( description="Content Release Tool" )
    arg_parser.add_argument( '-c', '--config', default=DEFAULT_CONFIG_FILE,
                             help="Configuration file. The default is: %s" % DEFAULT_CONFIG_FILE )
    arg_parser.add_argument( '--content-title', dest='content_title', help="The content title" )
    arg_parser.add_argument( '--content-version', dest='content_version', help="The content version" )
    arg_parser.add_argument( '-f', '--file', 
                             help="Content archive to release" )
    arg_parser.add_argument( '-p', '--contentpath',
                             help="The unpacked content to release" )
    return arg_parser.parse_args()

def main():
    # Parse the command line
    args = _parse_args()
    if args.contentpath:
        content_path = os.path.expanduser(args.contentpath)
    else:
        content_path = None
    if args.file:
        content_archive = os.path.expanduser(args.file)
    else:
        content_archive = None

    # Read the config file
    configfile = ConfigParser.SafeConfigParser()
    configfile.read( os.path.expanduser( args.config ) )

    # Build the effective config
    config = {}
    config['content-store'] = content_path or configfile.get('local', 'content-store')

    if content_archive and '.tgz' in content_archive:
        mark_for_release( config, get_content_metadata(content_archive) )
    elif content_path and os.path.isdir(content_path):
        if os.path.exists( os.path.join( content_path, '.version' ) ):
            mark_for_release( config, get_content_metadata(content_path) )
        else:
            print( '%s does not contain valid content' % content_path )
    else:
        print( 'No valid content found' )

if __name__ == '__main__': # pragma: no cover
        main()
