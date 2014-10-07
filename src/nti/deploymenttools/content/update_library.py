#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import get_content
from update_content import update_content

import argparse
import json
import os
import subprocess

import logging

logger = logging.getLogger('nti.deploymenttools.content')
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

def _process_bundle(bundle, bundle_name, base_path):
    if os.path.exists(os.path.join(base_path, '.svn')):
        logger.info("Updating %s to rev %s." % (bundle_name, bundle["svn-rev"]))
        old_cwd = os.getcwd()
        try:
            os.chdir(base_path)
            cmd = [
                'svn',
                'up',
                '-r', bundle["svn-rev"]
            ]
            subprocess.call( cmd )
        finally:
            os.chdir(old_cwd)
    else:
        logger.info("Checkout %s, rev %s to %s" % (bundle["svn-url"], bundle["svn-rev"],base_path))
        old_cwd = os.getcwd()
        try:
            os.chdir(base_path)
            cmd = [
                'svn',
                'co',
                bundle["svn-url"],
                '-r', bundle["svn-rev"],
                '.'
            ]
            subprocess.call( cmd )
        finally:
            os.chdir(old_cwd)

def _process_package(config, package, package_name, base_path):
    config['content-library'] = os.path.dirname(base_path)
    logger.debug(package_name)
    content = get_content( config=config, prefix=config['package-source'], title=package_name )[0]
    update_content( config, content, sharedWith=package['sharedWith'] )

def _process_library_contents(config, entry, entry_key, base_path):
    if 'svn-rev' in entry:
        _process_bundle(entry, entry_key, base_path)
    elif 'sharedWith' in entry:
        _process_package(config, entry, entry_key, base_path)
    elif 'site-src' in entry:
        catalog = {}
        with open( os.path.join(config['config-dir'], entry['site-src']), 'rb' ) as file:
            catalog = json.load( file )

        # Process the keys in 'Contents'
        _process_library_contents(config, catalog['Contents'], catalog['site-name'], base_path)
    else:
        for item in entry:
            if item == 'ContentPackageBundles':
                path = os.path.join(base_path, item)
                if not os.path.exists(path):
                    os.mkdir(path)
                _process_library_contents(config, entry[item], item, path)
            elif item == 'Packages':
                _process_library_contents(config, entry[item], item, base_path)
            else:
                path = os.path.join(base_path, item)
                if not os.path.exists(path):
                    os.mkdir(path)
                _process_library_contents(config, entry[item], item, path)

def update_library(config, catalog_file):
    catalog = {}
    with open( catalog_file, 'rb' ) as file:
        catalog = json.load( file )

    # Set the content package source
    config['package-source'] = catalog['package-source']

    # Process the keys in 'Contents'
    _process_library_contents(config, catalog['Contents'], catalog['environment-name'], config['content-library'])


DEFAULT_CONFIG_FILE='~/etc/nti_util_conf.ini'

def _parse_args():
    # Parse command line args
    arg_parser = argparse.ArgumentParser( description="Content Library Mangement Utility" )
    arg_parser.add_argument( '-l', '--content-library', dest='content_library', default='', 
                             help="Path from which the content is served from" )
    arg_parser.add_argument( '-s', '--content-store', dest='content_store', default='', 
                             help="Path to the content package collection" )
    arg_parser.add_argument( '--environment', default='prod', 
                             help="Defines which environment settings to use. Valid choices are 'alpha' and 'prod'." )
    arg_parser.add_argument( '-f', '--catalogfile', default='', 
                             help="A site-library catalog file." )
    return arg_parser.parse_args()

def main():
    args = _parse_args()
    catalogfile = os.path.expanduser( args.catalogfile )

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}
    config['environment'] = args.environment
    config['content-store'] = args.content_store
    config['content-library'] = args.content_library
    config['config-dir'] = os.path.dirname(catalogfile)

    update_library(config, catalogfile)

if __name__ == '__main__': # pragma: no cover
        main()