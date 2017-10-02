#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import argparse
import ConfigParser
import json
import os
import socket
import shutil
import subprocess
import tarfile
import tempfile
import time

def render_content( content_path ):
    content_name = os.path.basename( os.path.splitext( content_path )[0] )

    # Save the current working directory
    old_cwd = os.getcwd()
    # Change CWD to the content directory
    os.chdir( os.path.dirname( content_path ) )

    try:
        # Render the content
        print( 'Rendering %s' % os.path.basename(content_path) )
        cmd = [ 'nti_render', os.path.basename(content_path) ]
        subprocess.check_call( cmd )

        timestamp = time.strftime('%Y%m%d%H%M%S')

        content = { 'name': content_name,
                    'builder': socket.gethostname().split('.')[0].replace('-','_'),
                    'indexer': socket.gethostname().split('.')[0].replace('-','_'),
                    'version': timestamp,
                    'build_time': timestamp,
                    'index_time': timestamp }

        # Write content_info to .version
        with open( os.path.join( content_name, '.version' ), 'wb' ) as file:
            json.dump( content, file )

        # Build content archive
        print( 'Building content archive' )
        filename = '.'.join( [ '-'.join( [ content['name'], content['builder'], content['version'] ] ), 'tgz' ] )
        # Open the archive for writing and add the content to it
        with tarfile.open( name=filename, mode = 'w:gz' ) as archive:
            archive.add( content_name )

        content['archive'] = os.path.abspath( os.path.join( os.path.dirname( content_path ), filename ) )

    except subprocess.CalledProcessError:
        print("Failed to render %s" % content_name )
        content = None

    finally:
        # Clean-up
        if os.path.exists( '.'.join( [ content_name , 'paux' ] ) ):
            os.remove( '.'.join( [ content_name , 'paux' ] ) )

        if os.path.exists( content_name ):
            shutil.rmtree( content_name )

        # Restore the original CWD
        os.chdir( old_cwd )

    return content

def _parse_args():
    arg_parser = argparse.ArgumentParser( description="NTI Content Renderer" )
    arg_parser.add_argument( 'contentpath', help="Directory containing the content" )
    return arg_parser.parse_args()

def main():
    # Parse command line args
    args = _parse_args()
    content_path = os.path.abspath(os.path.expanduser(args.contentpath))

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}

    new_content = render_content( content_path )

if __name__ == '__main__': # pragma: no cover
        main()
