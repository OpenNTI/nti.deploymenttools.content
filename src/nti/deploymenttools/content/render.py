#!/usr/bin/env python

from __future__ import print_function

from argparse import ArgumentParser
from getpass import getpass
from shutil import rmtree
from socket import gethostname
from time import strftime

from nti.contentrendering import nti_render
from nti.deploymenttools.content import archive_directory
from nti.deploymenttools.content import upload_rendered_content

import logging
import os

logger = logging.getLogger('nti_render_content')
logging.captureWarnings(True)

UA_STRING = 'NextThought Local Render Utility'

def render_content( content_path, host, username, password, site_library, cleanup=True ):
    content_name = os.path.basename( os.path.splitext( content_path )[0] )

    # Save the current working directory
    old_cwd = os.getcwd()
    # Change CWD to the content directory
    os.chdir( os.path.dirname( content_path ) )

    # Build output archive name
    filename = '.'.join( [ content_name, 'zip' ] )
    content_archive = os.path.abspath( os.path.join( os.path.dirname( content_path ), filename ) )

    try:
        logger.info( 'Rendering %s' % os.path.basename(content_path) )
        # Render the content
        nti_render.render( os.path.basename(content_path), out_format='xhtml', nochecking=False)

        # Work around for nti_render.render not returning you to the original
        # working directory.
        os.chdir( os.path.dirname( content_path ) )

        logger.info( 'Building content archive' )
        archive_directory(content_name, content_archive)

        logger.info('Uploading render of %s to %s' % (content_name, host))
        upload_rendered_content( content_archive, host, username, password, site_library, UA_STRING )

    finally:
        # Clean-up
        if cleanup:
            if os.path.exists( '.'.join( [ content_name , 'paux' ] ) ):
                os.remove( '.'.join( [ content_name , 'paux' ] ) )

            if os.path.exists( content_archive ):
                os.remove( content_archive )

            if os.path.exists( content_name ):
                rmtree( content_name )

        # Restore the original CWD
        os.chdir( old_cwd )

def _parse_args():
    arg_parser = ArgumentParser( description=UA_STRING )
    arg_parser.add_argument( 'contentpath', help="Content driver file to render" )
    arg_parser.add_argument( '-s', '--server', dest='host',
                             help="Destination server for uploaded rendered content." )
    arg_parser.add_argument( '-u', '--user', dest='user',
                             help="User to authenticate with the server." )
    arg_parser.add_argument( '--site-library', dest='site_library',
                             help="Site library to add content to. Defaults to the hostname of the destination server." )
    arg_parser.add_argument( '-v', '--verbose', dest='loglevel', action='store_const', const=logging.DEBUG,
                             help="Print debugging logs." )
    arg_parser.add_argument( '-q', '--quiet', dest='loglevel', action='store_const', const=logging.WARNING,
                             help="Print warning and error logs only." )
    arg_parser.add_argument( '--no-cleanup', dest='no_cleanup', action='store_false', default=True,
                             help="Do not cleanup process files." )
    return arg_parser.parse_args()

def main():
    # Parse command line args
    args = _parse_args()
    content_path = os.path.abspath(os.path.expanduser(args.contentpath))

    site_library = args.site_library or args.host

    loglevel = args.loglevel or logging.INFO
    logger.setLevel(loglevel)
    nti_render.configure_logging(level=logging.getLevelName(loglevel))

    password = getpass('Password for %s@%s: ' % (args.user,args.host))

    render_content( content_path, args.host, args.user, password, site_library, cleanup=args.no_cleanup )

if __name__ == '__main__': # pragma: no cover
        main()
