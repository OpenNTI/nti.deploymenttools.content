#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import get_content, set_default_root_sharing
from . import create_delta_list
from . import get_all_published_content_metadata

import boto

import argparse
import ConfigParser
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time

def _inval_keys( keys_inval, access_key='', secret_key='', bucket='' ):
    if not keys_inval:
        print('Nothing to invalidate')
        return

    print('Invalidating necessary keys.')

    # Connect to CloudFront and invalidate necessary keys
    cfconn = boto.connect_cloudfront( access_key, secret_key )

    distribution_id = None
    for result in cfconn.get_all_distributions():
        if (bucket + '.s3.amazonaws.com') == result.get_distribution().config.origin.dns_name:
            distribution_id = result.get_distribution().id
            break

    inval_req = cfconn.create_invalidation_request( distribution_id, keys_inval )

    time_start = time.time()
    inval_req_status = cfconn.invalidation_request_status( distribution_id, inval_req.id ).status
    print( 'Invalidation status: %s Elapsed time: %ss' % (inval_req_status, (time.time()-time_start)) )
    while inval_req_status != 'Completed':
            time.sleep( 30 )
            inval_req_status = cfconn.invalidation_request_status( distribution_id, inval_req.id ).status
            print( 'Invalidation status: %s Elapsed time: %ss' % (inval_req_status, (time.time()-time_start)) )


def verify_content( config, content ):
    # Save the current working directory
    orig_working_dir = os.getcwd()

    # Create temporary working directory
    working_dir = tempfile.mkdtemp()

    inval_keys = []
    try:
        # Make it the current working directory
        os.chdir( working_dir )

        # Connect to S3
        s3conn = boto.connect_s3( config['aws-access-key'], config['aws-secret-key'] )

        # Fetch the metadata for the currently published version of the content from S3
        published_content = get_published_content_metadata( config, s3conn, content['name'] )

        # Check and see if the content version is not already published. If it is not current, then upload.
        if published_content is not  None and published_content['version'] == content['version']:
            print( '%s, version %s, has already been published.' % (content['name'], content['version']) )
        elif published_content is not  None and published_content['version'] > content['version']:
            print( 'A newer version of %s, version %s, has already been published.' % (content['name'], published_content['version']) )
        else:

            # Get the keys for the content from S3 before we update. This is necessary because we will use 
            # this listing to determine what keys need to be invalidated in CloudFront and CloudFront does not respond 
            # nicely to the request to invalidate non-existant keys.
            content_keys = []
            content_keys.extend( s3conn.get_bucket( config['publication-bucket'] ).list( prefix=content['name'] ) )


        content_list = []
        with tarfile.open( name=content['archive'] ) as archive:
            content_list.extend(archive.getnames())

    finally:
        # Clean-up
        os.chdir( orig_working_dir )
        if os.path.exists(working_dir):
            shutil.rmtree(working_dir)

    return inval_keys


def verify_published_content( config ):
    # Create a staging directory for content downloaded from S3
    staging_dir = tempfile.mkdtemp()

    try:
        # Connect to S3
        s3conn = boto.connect_s3( config['aws-access-key'], config['aws-secret-key'] )

        published_content_list = get_all_published_content_metadata( config, s3conn )

        inval_keys = []

        for published_content in published_content_list:
            content = get_content(config, prefix=config['content-prefix'], title=published_content['name'], version=published_content['version'])
            if content:
                content = content[0]
            

        #if 'content-store' in config and '.tgz' in config['content-store']:
        #    inval_keys = verify_content( config, get_content_metadata(config['content-store']) )
        #else:
        #    content_list = get_content( config, prefix=config['content-prefix'] )
        #    for content in content_list:
        #        inval_keys.extend( verify_content( config, content ) )

        # Invalidate necessary keys
        _inval_keys( inval_keys, access_key=config['aws-access-key'], secret_key=config['aws-secret-key'],
                     bucket=config['publication-bucket']) 

    finally:
        if os.path.exists( staging_dir ):
            shutil.rmtree( staging_dir )


DEFAULT_CONFIG_FILE='~/etc/nti_util_conf.ini'

def _parse_args():
    # Parse command line args
    arg_parser = argparse.ArgumentParser( description="NTI Content S3 Uploader" )
    arg_parser.add_argument( '-c', '--config', default=DEFAULT_CONFIG_FILE,
                             help="Configuration file. The default is: %s" % DEFAULT_CONFIG_FILE )
    arg_parser.add_argument( '-a', '--accesskey', default='', help="AWS access key" )
    arg_parser.add_argument( '-s', '--secretkey', default='', help="AWS secret key" )
    arg_parser.add_argument( '-b', '--bucket', default='', help="S3 bucket to publish the content to" )
    arg_parser.add_argument( '--environment', default='', 
                             help="Defines which environment settings to use. Valid choices are 'alpha' and 'prod'." )
    arg_parser.add_argument( '--use-released', dest='pool', action='store_const', const='release', default='release',
                             help="Forces the retrieval of content from the released pool." )
    arg_parser.add_argument( '--use-testing', dest='pool', action='store_const', const='testing', default='release',
                             help="Forces the retrieval of content from the testing pool." )
    arg_parser.add_argument( '--no-delta', dest='delta', action='store_false', default=True,
                             help="Upload the complete content instead of the changes." )
    arg_parser.add_argument( '--delta', dest='delta', action='store_true', default=True,
                             help="Upload the content changes instead of everything." )
    arg_parser.add_argument( '-p', '--contentpath', default='',
                             help="Directory containing the content directories" )
    return arg_parser.parse_args()

def main():
    # Parse the command line
    args = _parse_args()
    content_path = os.path.expanduser(args.contentpath)

    # Read the config file
    configfile = ConfigParser.SafeConfigParser()
    configfile.read( os.path.expanduser( args.config ) )

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}
    config['aws-access-key'] = args.accesskey or configfile.get('authentication', 'aws-access-key')
    config['aws-secret-key'] = args.secretkey or configfile.get('authentication', 'aws-secret-key')
    config['environment'] = args.environment or configfile.get('deployment', 'environment')
    config['publication-bucket'] = args.bucket or configfile.get('deployment', 'publication-bucket')
    config['staging-bucket'] = configfile.get('deployment', 'staging-bucket')
    config['content-store'] = content_path or configfile.get('local', 'content-store')
    config['content-prefix'] = args.pool

    verify_published_content( config )

if __name__ == '__main__': # pragma: no cover
        main()
