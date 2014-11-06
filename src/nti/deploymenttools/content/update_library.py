#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import get_content
from . import get_svn_revision
from . import _update_content

import argparse
import codecs
import json
import os
import subprocess
import shutil
import tarfile
import tempfile

import logging

logger = logging.getLogger('nti.deploymenttools.content')
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
log_handler.setLevel(logging.INFO)
logger.addHandler(log_handler)

def _process_bundle(bundle, bundle_name, base_path):
    if os.path.exists(os.path.join(base_path, '.svn')):
        current_rev = get_svn_revision(base_path)
        if (current_rev != bundle["svn-rev"]):
            logger.info("Updating %s to from rev %s to %s." % (bundle_name, current_rev, bundle["svn-rev"]))
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

def _process_course_info_overrides(course_info_file, overrides):
    course_info = None
    if os.path.exists(course_info_file):
        with codecs.open(course_info_file, 'rb', 'utf-8') as file:
            course_info = json.load(file)
    else:
        course_info = {}

    for key in overrides:
        course_info[key] = overrides[key]

    with codecs.open(course_info_file, 'wb', 'utf-8') as file:
        json.dump( course_info, file, indent=4, separators=(',', ': '), sort_keys=True )
        file.write('\n')

def _process_package(config, package, package_name, base_path):
    config['content-library'] = os.path.dirname(base_path)
    version = ''
    if 'version' in package:
        version = package['version']
    content = None
    packages = get_content( config=config, prefix=config['package-source'], title=package_name, version=version )
    if len(packages > 0):
        content = packages[0]
    else:
        logger.warning('No content package found for %s.' % package_name)
        return
    _update_content( config, content, sharedWith=package['sharedWith'] )
    key = u'presentation-assets'
    if key in package:
        path = os.path.join(base_path, key)
        if not os.path.exists(path):
            os.mkdir(path)
        elif not os.path.exists(os.path.join(path,u'.svn')):
            shutil.rmtree(path)
            os.mkdir(path)
        _process_bundle(package['presentation-assets'], 'presentation-assets', path)
    key = u'course_info_override'
    if key in package:
        path = os.path.join(base_path, 'course_info.json')
        _process_course_info_overrides(path, package[key])

def _process_dictionary(config, dictionary, dictionary_name, base_path):
    # Create a temporary working directory
    working_dir = tempfile.mkdtemp()
    # Store the current working directory
    orig_dir = os.getcwd()
    # Change the current working directory to the temp directory
    os.chdir( working_dir )

    try:
        # Get dictionary archive
        logger.debug('Downloading dictionary: %s' % dictionary_name)
        cmd = ['wget', '-q', dictionary['dictionary-src'] ]
        subprocess.check_call( cmd )

        # Unpack the dictionary archive
        logger.debug('Unpacking dictionary: %s' % dictionary_name)
        with tarfile.open( name=os.path.basename(dictionary['dictionary-src']) ) as archive:
            archive.extractall()

        # Rsync the dictionary archive
        logger.debug('Updating dictionary: %s' % dictionary_name)
        cmd = [ 'rsync', '-a', '--delete', os.path.join( working_dir, dictionary_name), os.path.dirname(base_path) ]
        subprocess.check_call( cmd )
    finally:
        # Clean-up
        os.chdir(orig_dir)
        shutil.rmtree(working_dir)

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
    elif 'dictionary-src' in entry:
        _process_dictionary(config, entry, entry_key, base_path)
    else:
        for item in entry:
            if item == 'Dictionaries':
                _process_library_contents(config, entry[item], item, base_path)
            elif item == 'Packages':
                _process_library_contents(config, entry[item], item, base_path)
            else:
                logger.debug("Processing %s:" % item)
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
    arg_parser.add_argument( '-f', '--catalogfile', default='', 
                             help="A site-library catalog file." )
    return arg_parser.parse_args()

def main():
    args = _parse_args()
    catalogfile = os.path.abspath(os.path.expanduser( args.catalogfile ))

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}
    config['environment'] = 'prod'
    config['content-store'] = os.path.abspath(os.path.expanduser(args.content_store))
    config['content-library'] = os.path.abspath(os.path.expanduser(args.content_library))
    config['config-dir'] = os.path.dirname(catalogfile)

    update_library(config, catalogfile)

if __name__ == '__main__': # pragma: no cover
        main()
