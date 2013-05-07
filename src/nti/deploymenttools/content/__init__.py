#!/usr/bin/python

from __future__ import unicode_literals, print_function

from hashlib import sha256

import importlib
import json
import os
import shutil
import subprocess
import sys
import tarfile

def compare_files( file_1, file_2 ):
    """Computes the hashes for file_1 and file_2 and returns if they are equal or not"""
    # Compute the hash for file 1
    with open( file_1, 'rb' ) as file:
        hash_1 = sha256(file.read()).hexdigest()
    # Compute the hash for file 2
    with open( file_2, 'rb' ) as file:
        hash_2 = sha256(file.read()).hexdigest()

    return ( hash_1 == hash_2 )

def create_delta_list( dir_1, dir_2 ):
    """Assembles the delta between dir_1 and dir_2 and returns the tuple (delta, removed_files). Where 'delta' is the path of the directory containing the files in dir_2 that were added or changed form dir_1 and 'removed_files' is a list of the files in dir_1 not in dir_2."""

    # Traverse and build the list of files in dir_1
    dir_1_files = []
    for root, dirs, files in os.walk(dir_1):
        for file in files:
            dir_1_files.append(os.path.join(root.replace(dir_1+'/', ''), file))

    # Traverse and build the list of files in dir_2
    dir_2_files = []
    for root, dirs, files in os.walk(dir_2):
        for file in files:
            dir_2_files.append(os.path.join(root.replace(dir_2+'/', ''), file))

    # First find the files that have changed. Then find the dir_1 files that are not present in dir_2. Finally find the files in the dir_2 that were not present in dir_1.
    delta_files = []
    added_files = []
    removed_files = []
    for file in dir_1_files:
        
        if os.path.exists(os.path.join(dir_2, file)):
            # If the files are not the same, add the 'new' file to the delta file list
            if os.path.isfile(file) and not compare_files( os.path.join(dir_1, file), os.path.join( dir_2, file ) ):
                delta_files.append(file)
        else:
            removed_files.append(file)

    for file in dir_2_files:
        if not os.path.exists(os.path.join(dir_1, file)):
            delta_files.append( file )
            added_files.append( file )

    return delta_files, added_files, removed_files

def get_content_metadata( content_package ):
    if '.tgz' in content_package:
        return _get_content_metadata_packed( content_package )
    else:
        return _get_content_metadata_unpacked( content_package )

def _get_content_metadata_packed( content_package ):
    (name, builder, timestamp) = os.path.splitext(os.path.basename(content_package))[0].split('-')
    with tarfile.open( content_package ) as tarball:
        member_name = os.path.join( name, '.version' )
        if member_name in tarball.getnames():
            content = json.load( tarball.extractfile( member_name ) )
        else:
            content = { 'name': name,
                        'builder': builder,
                        'indexer': builder,
                        'version': timestamp,
                        'build_time': timestamp,
                        'index_time': timestamp }
        content['archive'] = os.path.abspath(content_package)

    return content

def _get_content_metadata_unpacked( content_package ):
    content = None
    version_file = os.path.join( content_package, '.version' )
    if os.path.exists( version_file ):
        with open( version_file, 'rb' ) as file:
            content = json.load( file )

    return content

def get_published_content_metadata( config, s3conn, content_title ):
    content = None
    key = s3conn.get_bucket( config['publication-bucket'] ).get_key( '/'.join( [content_title, '.version'] ) )
    if key:
        content = json.loads(key.get_contents_as_string())
    return content

def _get_content( content_store='.', prefix='testing', title='', version='', all_versions=False ):
    """This method retrieves content from the local filesystem content store. 
    The name variable specifies the desired content title. The version 
    variable specifies the desired version of a content title. If name and 
    version are unspecified then it will retrieve the latest content package 
    for each content title found in the local store.
    NOTE: Does not yet return all mathcing content when requested."""

    archives = {}
    # Get the items in the directory content_path
    for item in os.listdir( os.path.join( content_store, prefix ) ):
        filename = os.path.join( content_store, prefix, item )
        # The item is a file and contains .tgz assume it is a content archive.  This is potentially dangerous.
        if os.path.isfile( filename ) and '.tgz' in filename:
            _t = get_content_metadata( filename )

            if title is not '' and title != _t['name']:
                continue

            if title is not '' and version is not '':
                if title == _t['name'] and version == _t['version']:
                    archives[_t['name']] = _t
                    break
            else:
                if _t['name'] in archives:
                    # Check and see if the current item is the newest archive for that content.
                    # If this is the newest, update the tracking list
                    if archives[_t['name']]['version'] < _t['version']:
                        archives[_t['name']] = _t
                else:
                    # We have not seen this content before so add it.
                    archives[_t['name']] = _t

    # Build a simple list to return to the caller
    content_list = []
    for archive in archives:
        content_list.append( archives[archive] )

    return content_list

def get_content( config=None, prefix='testing', title='', version='', all_versions=False ):
    """Public method used to retrive content and most abstract away the 
    differences in fetching content from S3 and a local content store."""

    if not config:
        raise Exception("Must pass a config object")

    # Get content from the local store
    content_list = _get_content( config['content-store'], prefix, title, version, all_versions )

    return content_list

def move_content( config, content, dest='' ):
    if dest and os.path.exists( os.path.join( config['content-store'], dest ) ):
        new_loc = os.path.join( config['content-store'], dest, 
                                '-'.join( [ content['name'], content['builder'], content['version'] ] ) + '.tgz' )
        shutil.move( content['archive'], new_loc )
        content['archive'] = new_loc
    return content

def symlink_content( config, content, dest='' ):
    if dest and os.path.exists( os.path.join( config['content-store'], dest ) ):
        old_cwd = os.getcwd()
        try:
            os.chdir( os.path.join( config['content-store'], dest ) )
            rel_path = os.path.relpath( content['archive'] )
            filename = '-'.join( [ content['name'], content['builder'], content['version'] ] ) + '.tgz'
            os.symlink( rel_path, filename )
            content['archive'] = os.path.join( config['content-store'], dest, filename )
        finally:
            os.chdir(old_cwd)
    return content

def put_content( config, content_list=None, dest='testing' ):
    """This method moves the content in content_list into the local filesystem 
    content store described by content_store"""

    # Leave if there is no content to update
    if not content_list:
        return

    if os.path.exists( config['content-store'] ):
        for content in content_list:
            move_content( config, content, dest )

def set_default_root_sharing( content, environment = 'prod' ):
    filename = os.path.join( os.path.dirname( __file__ ), 'default_sharing.json' )
    with open( filename, 'rb' ) as file:
        default_root_sharing = json.load( file )[environment]

    if os.path.basename(content) in default_root_sharing:
        print( 'Setting default root sharing group on %s' % os.path.basename(content) )
        cmd = [ 'nti_default_root_sharing_setter',
                content,
                '-g', default_root_sharing[os.path.basename(content)]
                ]
        subprocess.check_call( cmd )
