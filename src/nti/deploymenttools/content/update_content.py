#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import get_content, get_content_metadata, set_default_root_sharing

import argparse
import ConfigParser
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

from functools import partial
from multiprocessing import Pool

import logging

logger = logging.getLogger('nti.deploymenttools.content')
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

def update_content( config, content , sharedWith=None ):
    content_dir = os.path.join( config['content-library'], content['name'] )

    # If the content directory does not exist, then create it.
    if not os.path.exists( content_dir ):
        os.makedirs( content_dir )

    # Check if the content is current
    version_file = os.path.join( config['content-library'], content['name'], '.version' )
    if os.path.exists( version_file ):
        existing_content = None
        with open( version_file, 'rb' ) as file:
                existing_content = json.load( file )
        if existing_content and existing_content['version'] == content['version']:
            # The content has already been updated, do not repeat
            logger.debug( '%s is already up to date.' % content['name'] )
            return
        else:
            logger.info('Updating %s from version %s to %s' % (content['name'], existing_content['version'], content['version']))
    else:
        logger.info('No version file found. Updating %s' % content['name'])

    # Create a temporary working directory
    working_dir = tempfile.mkdtemp()
    # Store the current working directory
    orig_dir = os.getcwd()
    # Change the current working directory to the temp directory
    os.chdir( working_dir )

    try:
        # Unpack the content archive
        logger.debug('Unpacking the %s archive' % content['name'])
        with tarfile.open( name=content['archive'] ) as archive:
            archive.extractall()

        # Add .version file if not present
        if not os.path.exists( os.path.join(content['name'] , '.version') ):
            with open( os.path.join(content['name'] , '.version'), 'wb' ) as file:
                _t = content.pop('archive')
                json.dump( content, file )
                content['archive'] = _t

        # Set the default root sharing
        set_default_root_sharing( os.path.join( working_dir, content['name']), config['environment'], sharedWith=sharedWith )

        # Rsync the new content over the old and delete the differences
        logger.debug('Updating %s' % content['name'])
        cmd = [ 'rsync', '-a', '--delete', os.path.join( working_dir, content['name']), config['content-library'] ]
        subprocess.check_call( cmd )
    finally:
        # Clean-up
        os.chdir(orig_dir)
        shutil.rmtree(working_dir)    

DEFAULT_CONFIG_FILE='~/etc/nti_util_conf.ini'

def _parse_args():
    # Parse command line args
    arg_parser = argparse.ArgumentParser( description="Content Updater" )
    arg_parser.add_argument( '-c', '--config', default=DEFAULT_CONFIG_FILE,
                             help="Configuration file. The default is: %s" % DEFAULT_CONFIG_FILE )
    arg_parser.add_argument( '-j', dest='process_pool_size', type=int, default='4', 
                             help="Number of processes used when updating content. The default is four." )
    arg_parser.add_argument( '-l', '--content-library', dest='content_library', default='', 
                             help="Path from which the content is served from" )
    arg_parser.add_argument( '--environment', default='', 
                             help="Defines which environment settings to use. Valid choices are 'alpha' and 'prod'." )
    arg_parser.add_argument( '-p', '--contentpath', default='', 
                             help="A content archive or a directory containing content archives" )
    arg_parser.add_argument( '--use-dev', dest='pool', action='store_const', const='development', default='testing',
                             help="Forces the retrieval of content from the development pool." )
    arg_parser.add_argument( '--use-released', dest='pool', action='store_const', const='release', default='testing',
                             help="Forces the retrieval of content from the released pool." )
    arg_parser.add_argument( '--use-testing', dest='pool', action='store_const', const='testing', default='testing',
                             help="Forces the retrieval of content from the testing pool." )
    arg_parser.add_argument( '--use-uat', dest='pool', action='store_const', const='uat', default='testing',
                             help="Forces the retrieval of content from the UAT pool." )
    return arg_parser.parse_args()

def main():
    args = _parse_args()
    content_path = os.path.expanduser(args.contentpath)

    # Read the config file
    configfile = ConfigParser.SafeConfigParser()
    configfile.read( os.path.expanduser( args.config ) )

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}
    config['environment'] = args.environment or configfile.get('deployment', 'environment')
    config['content-store'] = content_path or configfile.get('local', 'content-store')
    config['content-library'] = args.content_library or configfile.get('local', 'content-library')

    # Create a staging directory for content downloaded from S3
    staging_dir = tempfile.mkdtemp()

    try:
        if '.tgz' in config['content-store']:
            update_content( config, get_content_metadata(content_path) )
        else:
            latest_content = get_content( config=config, prefix=args.pool )
            process_pool = Pool(processes=args.process_pool_size)
            partial_update_content = partial(update_content, config)
            process_pool.map_async(partial_update_content, latest_content)
            process_pool.close()
            process_pool.join()
    finally:
        if os.path.exists( staging_dir ):
            shutil.rmtree( staging_dir )

if __name__ == '__main__': # pragma: no cover
        main()
