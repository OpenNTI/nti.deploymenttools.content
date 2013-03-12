#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import boto
from boto.s3.key import Key

from . import get_content, move_content, put_content

import argparse
import ConfigParser
import json
import os
import shutil
import socket
import subprocess
import tarfile
import tempfile
import time

def reindex_content( content, output_dir='.' ):

    # Create a temporary working directory
    working_dir = tempfile.mkdtemp()
    # Store the current working directory
    orig_dir = os.getcwd()
    # Change the current working directory to the temp directory
    os.chdir( working_dir )

    try:
        # Extract the content archive
        print( 'Extracting content archive %s' % content['archive'] )
        with tarfile.open( name=content['archive'] ) as archive:
            archive.extractall()

        # Reindex the content
        print( 'Reindexing %s' % content['name'] )
        cmd = [ 'nti_index_book_content', content['name'] ]
        subprocess.check_call( cmd )

        # Update content metadata and .version file
        timestamp = time.strftime('%Y%m%d%H%M%S')
        content['indexer'] = socket.gethostname().split('.')[0]
        content['index_time'] = timestamp
        content['version'] = timestamp

        # Write content_info to .version
        content.pop( 'archive' )
        with open( os.path.join( content['name'], '.version' ), 'wb' ) as file:
            json.dump( content, file )

        # Build a new content archive
        print( 'Building new content archive' )
        filename = '.'.join( [ '-'.join( [ content['name'], content['builder'], content['version'] ] ), 'tgz' ] )
        # Open the new archive for writing and add the re-indexed content to it
        with tarfile.open( name=filename, mode = 'w:gz' ) as archive:
            archive.add( content['name'] )

        content['archive'] = os.path.abspath( os.path.join( working_dir, filename ) )

        # Move the new archive to the content output directory
        new_loc = os.path.join( output_dir, filename )
        shutil.move( content['archive'], new_loc )
        content['archive'] = os.path.abspath( new_loc )

    except subprocess.CalledProcessError:
        print("Failed to reindex %s" % content.name )
        content = None

    finally:
        # Return to the original working directory
        os.chdir( orig_dir )
        # Remove the temp directory
        shutil.rmtree( working_dir )

    return content

DEFAULT_CONFIG_FILE='~/etc/nti_util_conf.ini'

def _parse_args():
    arg_parser = argparse.ArgumentParser( description="Content Re-indexer" )
    arg_parser.add_argument( '-c', '--config', default=DEFAULT_CONFIG_FILE, 
                             help="Configuration file. The default is: %s" % DEFAULT_CONFIG_FILE )
    arg_parser.add_argument( '-f', '--contentpath', default='', help="Directory containing the content archives" )
    arg_parser.add_argument( '-t', '--content-title', dest='content_title', default='', 
                             help="Directory containing the content archives" )
    return arg_parser.parse_args()

def main():
    # Parse command line args
    args = _parse_args()
    content_path = os.path.expanduser(args.contentpath)

    # Read the config file
    configfile = ConfigParser.SafeConfigParser()
    configfile.read( os.path.expanduser( args.config ) )

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}
    config['content-store'] = content_path or configfile.get('local', 'content-store')

    # Create a temporary content output directory
    content_output = tempfile.mkdtemp()

    try:
        content_list = []
        if content_path and '.tgz' in content_path:
            new_content = reindex_content( _Content.fromTarball(content_path), output_dir=content_output )
            if new_content:
                content_list.append(new_content)
        else:
            latest_content = get_content( config=config, title=args.content_title )
            for content in latest_content:
                new_content = reindex_content( content, output_dir=content_output )
                if new_content:
                    content_list.append(new_content)

        put_content( config, content_list )

    finally:
        # Clean-up after ourselves
        if os.path.exists( content_output ):
            shutil.rmtree( content_output )

if __name__ == '__main__': # pragma: no cover
        main()
