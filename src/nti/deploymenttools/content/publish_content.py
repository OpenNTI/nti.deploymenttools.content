#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from . import get_content, set_default_root_sharing
from . import create_delta_list
from . import get_published_content_metadata

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

def _push_content( content, access_key='', secret_key='',  bucket='' ):
    # upload the new content.
    print( 'Uploading content' )

    # Upload the content
    prefix = os.path.split( content )[0]
    cmd = [ 'nti_s3put',
            '-r',
            '-a', access_key,
            '-s', secret_key,
            '-b', bucket,
            '-g', 'public-read',
            '-p', prefix,
            os.path.basename( content )
            ]
    subprocess.check_call( cmd )

def _build_inval_list( keys ):
    keys_inval = []

    for key in keys:
        if 'eclipse-toc.xml' in key.name:
            keys_inval.append( '/' + key.name )
        elif 'html' in key.name:
            keys_inval.append( '/' + key.name )

    return keys_inval

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

def create_content_delta( config, working_dir, old_content, new_content ):
    """Constructs a directory that contains a only the files add/changed between old_content and new_content and a list of the files in old_content not present in new_content."""

    # Save the current working directory
    orig_working_dir = os.getcwd()

    # Build directory structure
    old_dir = os.path.join( working_dir, 'old' )
    new_dir = os.path.join( working_dir, 'new' )
    delta_dir = working_dir

    try:
        os.mkdir(old_dir)
        os.mkdir(new_dir)

        # Get and unpack the existing content
        os.chdir(old_dir)
        old_content = get_content( config, prefix=config['content-prefix'], title=old_content['name'], version=old_content['version'] )[0]
        with tarfile.open( name=old_content['archive'] ) as archive:
            archive.extractall()

        # Unpack the new content
        os.chdir(new_dir)
        with tarfile.open( name=new_content['archive'] ) as archive:
            archive.extractall()

        # Create the delta content
        delta_files, added_files, removed_files = create_delta_list( old_dir, new_dir )
        for file in delta_files:
            delta_path = os.path.join( delta_dir,  os.path.dirname(file) )
            if not os.path.exists( delta_path ):
                os.makedirs( delta_path )
            os.link( os.path.join( new_dir, file ), os.path.join( delta_dir, file ) )
    finally:
        # Return to the original working directory
        os.chdir(orig_working_dir)

        # Remove old_dir and new_dir
        if os.path.exists( old_dir ):
            shutil.rmtree( old_dir )
        if os.path.exists( new_dir ):
            shutil.rmtree( new_dir )

    return added_files, removed_files

def upload_content( config, content ):
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
            if published_content is None:
                # Unpack the content archive
                print('Unpacking %s' % content['name'] )
                with tarfile.open( name=content['archive'] ) as archive:
                    archive.extractall()
                removed_files = []
            else:
                print('Calculating the delta between %s version %s and %s.' % (content['name'], published_content['version'], content['version']) )
                added_files, removed_files = create_content_delta( config, working_dir, published_content, content )

            # Add .version file if not present
            if not os.path.exists( os.path.join(content['name'] , '.version') ):
                with open( os.path.join(content['name'] , '.version'), 'wb' ) as file:
                    _t = content.pop('archive')
                    json.dump( content, file )
                    content['archive'] = _t

            # Only set default sharing if the 'eclipse-toc.xml' file exists.  The only time it would not
            # exist is for content updates where the toc does not change.
            if os.path.exists( os.path.join(content['name'] , 'eclipse-toc.xml' ) ):
                set_default_root_sharing( content['name'], environment = config['environment'] )

            # Get the keys for the content from S3 before we update. This is necessary because we will use 
            # this listing to determine what keys need to be invalidated in CloudFront and CloudFront does not respond 
            # nicely to the request to invalidate non-existant keys.
            content_keys = []
            content_keys.extend( s3conn.get_bucket( config['publication-bucket'] ).list( prefix=content['name'] ) )

            # Send the content to the S3 Prod or Alpha bucket
            _push_content( os.path.abspath(content['name']), access_key=config['aws-access-key'], 
                           secret_key=config['aws-secret-key'], bucket=config['publication-bucket'] )

            # Build the list of keys to be invalidated for this content
            inval_keys = _build_inval_list( content_keys )

            # Find keys leftover from previous versions of the content and delete them
            for key in content_keys:
                if key.name in removed_files:
                    print( 'Deleting leftover key: %s' % key.name )
                    key.delete()
    finally:
        # Clean-up
        os.chdir( orig_working_dir )
        if os.path.exists(working_dir):
            shutil.rmtree(working_dir)

    return inval_keys

def publish_content( config ):
    # Create a staging directory for content downloaded from S3
    staging_dir = tempfile.mkdtemp()

    try:
        inval_keys = []
        if 'content-store' in config and '.tgz' in config['content-store']:
            inval_keys = upload_content( config, get_content_metadata(config['content-store']) )
        else:
            content_list = get_content( config, prefix=config['content-prefix'] )
            for content in content_list:
                inval_keys.extend( upload_content( config, content ) )

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

    publish_content( config )

if __name__ == '__main__': # pragma: no cover
        main()
