#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import get_content_metadata
from . import get_from_catalog
from . import symlink_content
from . import update_catalog

import argparse
import codecs
import ConfigParser
import json
import logging
import os
import subprocess

from xml.dom import minidom

logger = logging.getLogger('nti.deploymenttools.content')
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
log_handler.setLevel(logging.INFO)
logger.addHandler(log_handler)

def _check_svn_revision( working_copy_path ):
    revision = None

    try:
        cmd = ['svn', 'info', '--xml', working_copy_path]
        process = subprocess.Popen(cmd, bufsize=-1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        dom = minidom.parseString(stdout)
        commit_nodes = dom.getElementsByTagName('commit')
        if len(commit_nodes) > 0:
            revision = commit_nodes[0].getAttribute('revision')

    except:
        logger.error(stderr)

    return revision

def _read_global_catalog( catalog_file ):
    catalog = {}
    with codecs.open( catalog_file, 'rb', 'utf-8' ) as file:
        catalog['global'] = json.load( file )

    if 'sites' in catalog['global']['Contents']:
        for site in catalog['global']['Contents']['sites']:
            filename = os.path.join(os.path.dirname(catalog_file), catalog['global']['Contents']['sites'][site]['site-src'])
            with codecs.open( filename, 'rb', 'utf-8' ) as file:
                catalog[site] = json.load( file )

    return catalog

def _write_global_catalog( catalog_file, catalog ):
    with codecs.open( catalog_file, 'wb', 'utf-8' ) as file:
        json.dump( catalog['global'], file, indent=4, separators=(',', ': '), sort_keys=True )
        file.write('\n')

    catalog_dir = os.path.dirname(catalog_file)
    for site in catalog:
        if site != u'global':
            filename = os.path.join(catalog_dir, catalog['global']['Contents']['sites'][site]['site-src'])
            with codecs.open( filename, 'wb', 'utf-8' ) as file:
                json.dump( catalog[site], file, indent=4, separators=(',', ': '), sort_keys=True )
                file.write('\n')

def _read_bundle_metadata( bundle ):
    bundle_data = None
    bundle_file = os.path.join(bundle, 'bundle_meta_info.json')
    if os.path.exists(bundle_file):
        with codecs.open( bundle_file, 'rb', 'utf-8' ) as file:
            bundle_data = json.load( file )
    return bundle_data

def _find_bundle_packages( bundle_metadata, site_path ):
    def _get_toc_ntiid( toc_file ):
        toc_ntiid = None
        with open( toc_file, 'rb' ) as file:
            toc = minidom.parse( file )
            toc_nodes = toc.getElementsByTagName('toc')
            if len(toc_nodes) > 0:
                toc_ntiid = toc_nodes[0].getAttribute('ntiid')
        return toc_ntiid

    bundle_packages = []
    bundle_package_ntiids = bundle_metadata['ContentPackages']
    site_dir = os.path.join(site_path[-1],site_path[-2])
    for package in os.listdir(site_dir):
        toc_file = os.path.join(site_dir, package, 'eclipse-toc.xml')
        if os.path.exists(toc_file):
            toc_ntiid = _get_toc_ntiid(toc_file)
            if toc_ntiid in bundle_package_ntiids:
                if os.path.exists(os.path.join(site_dir, package, '.version')):
                    bundle_packages.append(get_content_metadata(os.path.join(site_dir, package)))
    return bundle_packages

def mark_bundle_for_release( config, bundle, dest='release' ):
    def _get_site_path( bundle_path ):
        path, basename = os.path.split(os.path.abspath(bundle_path))
        site_path = []
        while basename != u'/':
            if basename == u'sites':
                site_path.append(os.path.join(path,basename))
                break
            site_path.append(basename)
            path, basename = os.path.split(path)
        return site_path

    catalog = _read_global_catalog(config['catalog-file'])
    revision = _check_svn_revision( bundle )
    bundle_metadata = _read_bundle_metadata( bundle )
    site_path = _get_site_path( bundle )
    bundle_packages = _find_bundle_packages( bundle_metadata, site_path )
    site_catalog = catalog[site_path[-2]]

    if revision is not None:
        bundle_entry = site_catalog['Contents'][site_path[2]][site_path[1]][site_path[0]]
        bundle_entry['svn-rev'] = revision

    if len(bundle_packages) > 0:
        for bundle_package in bundle_packages:
            site_catalog['Contents']['Packages'][bundle_package['name']]['version'] = bundle_package['version']
            mark_package_for_release(config, bundle_package, dest)

    _write_global_catalog( config['catalog-file'], catalog )

def mark_package_for_release( config, content, dest='release' ):
    logger.info( 'Marking %s version %s for %s.' % ( content['name'], content['version'], dest ) )
    entry = get_from_catalog(config['content-store'], title=content['name'], version=content['version'])
    if entry:
        symlink_content( config, entry[0], dest )
        entry[0]['state'].append(dest)
        update_catalog(config['content-store'], entry)
    else:
        logger.warning('Unable to find %s, version %s, in the catalog' % ( content['name'], content['version'] ) )

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
                             help="The unpacked content or bundle to release" )
    arg_parser.add_argument( '--catalog-file', dest='catalog_file',
                             help="The global catalog file for the desired environment." )
    arg_parser.add_argument( '--use-release', dest='pool', action='store_const', const='release', default='release',
                             help="Release the content to the release pool." )
    arg_parser.add_argument( '--use-uat', dest='pool', action='store_const', const='uat', default='release',
                             help="Release the content to the UAT pool." )
    return arg_parser.parse_args()

def main():
    # Parse the command line
    args = _parse_args()
    if args.contentpath:
        content_path = os.path.abspath(os.path.expanduser(args.contentpath))
    else:
        content_path = None
    if args.file:
        content_archive = os.path.abspath(os.path.expanduser(args.file))
    else:
        content_archive = None
    if args.catalog_file:
        catalog_file = os.path.abspath(os.path.expanduser(args.catalog_file))
    else:
        catalog_file = None

    # Read the config file
    configfile = ConfigParser.SafeConfigParser()
    configfile.read( os.path.expanduser( args.config ) )

    # Build the effective config
    config = {}
    config['content-store'] = configfile.get('local', 'content-store')
    config['catalog-file'] = catalog_file

    if content_archive and '.tgz' in content_archive:
        mark_package_for_release( config, get_content_metadata(content_archive), dest=args.pool )
    elif content_path and os.path.isdir(content_path):
        if os.path.exists( os.path.join( content_path, '.version' ) ):
            mark_package_for_release( config, get_content_metadata(content_path), dest=args.pool )
        elif os.path.exists( os.path.join( content_path, 'bundle_meta_info.json' ) ):
            mark_bundle_for_release( config, content_path, dest=args.pool )
        else:
            logger.warning( '%s does not contain valid content' % content_path )
    else:
        logger.warning( 'No valid content found' )

if __name__ == '__main__': # pragma: no cover
        main()
