#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import boto

import argparse
import codecs
import hashlib
import os
import shutil
import subprocess
import sys


from lxml import etree


def _get_file_hash( filename ):
    """SAJ: Based on code at http://www.pythoncentral.io/hashing-files-with-python/"""
    hasher = hashlib.md5()
    BLOCKSIZE = 65536
    with open( filename, 'rb' ) as infile:
        buf = infile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = infile.read(BLOCKSIZE)
    return hasher.hexdigest()

def _version_files( file_list ):
    
    asset_fwd_map = {}
    asset_rev_map = {}
    
    orig_cwd = os.getcwd()
    for file in file_list:
        os.chdir(os.path.dirname(os.path.abspath(file)))
        doc = None
        with open(file, "rb") as f:
            doc =  etree.parse(f, etree.HTMLParser())
            for node in doc.iter():
                if 'src' in node.attrib and os.path.exists(node.attrib['src']):
                    src = os.path.abspath(node.attrib['src'])
                    if src in asset_fwd_map:
                        file_hash = asset_fwd_map[src]
                    else:
                        file_hash = _get_file_hash(src)
                        asset_fwd_map[src] = file_hash
                        if file_hash in asset_rev_map:
                            asset_rev_map[file_hash].append(src)
                        else:
                            asset_rev_map[file_hash] = [src]
                    new_filename = os.path.splitext(node.attrib['src'])[0]+u'-'+file_hash+os.path.splitext(node.attrib['src'])[1]
                    node.attrib['src'] = new_filename
        with open(file, 'wb') as f:
            f.write(etree.tostring(doc.getroot(), pretty_print=True, method="html"))

        os.chdir(orig_cwd)

    # Copy the asset to the new name
    for asset in asset_fwd_map:
        new_filename = os.path.splitext(asset)[0]+u'-'+asset_fwd_map[asset]+os.path.splitext(asset)[1]
        shutil.copy(asset,new_filename)

def _push_content( file, access_key='', secret_key='',  bucket='' , prefix='', headers=[] ):
    # Upload the content
    cmd = [ 's3put',
            '-r',
            '-w',
            '-a', access_key,
            '-s', secret_key,
            '-b', bucket,
            '-g', 'public-read',
            '-p', prefix
            ]
    for header in headers:
        cmd.extend(['--header', header])
    cmd.append( file )

    #print(' '.join(cmd))
    subprocess.check_call( cmd )


def publish_landing_page( config ):

    file_list = []
    for root, dirs, files in os.walk(config['content-path']):
        for file in files:
            if '.html' in file:
                file_list.append(os.path.join(root, file))
    _version_files( file_list )

    headers = ['Cache-Control=max-age=3600']
    _push_content(config['content-path'], access_key=config['aws-access-key'], secret_key=config['aws-secret-key'], bucket=config['bucket'], prefix=config['prefix'], headers=headers)

def _parse_args():
    # Parse command line args
    arg_parser = argparse.ArgumentParser( description="NTI Landing Page S3 Uploader" )
    arg_parser.add_argument( '-a', '--accesskey', default='', help="AWS access key" )
    arg_parser.add_argument( '-s', '--secretkey', default='', help="AWS secret key" )
    arg_parser.add_argument( '-b', '--bucket', default='', help="S3 bucket to publish the content to" )
    arg_parser.add_argument( '-p', '--prefix', default='', 
                             help="A file path prefix that will be stripped from the full path of the file when determining the key name in S3." )
    arg_parser.add_argument( 'contentpath', default='.',
                             help="Directory containing the landing page." )
    return arg_parser.parse_args()

def main():
    # Parse the command line
    args = _parse_args()
    content_path = os.path.expanduser(args.contentpath)

#    # Read the config file
#    configfile = ConfigParser.SafeConfigParser()
#    configfile.read( os.path.expanduser( args.config ) )

    # Build the effective config. This will be important when all of the command line arguments are hooked up.
    config = {}
    config['aws-access-key'] = args.accesskey
    config['aws-secret-key'] = args.secretkey
    config['bucket'] = args.bucket
    config['content-path'] = content_path
    config['prefix'] = args.prefix

    publish_landing_page( config )

if __name__ == '__main__': # pragma: no cover
        main()
