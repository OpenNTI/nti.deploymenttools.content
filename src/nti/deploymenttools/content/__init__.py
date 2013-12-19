#!/usr/bin/python

from __future__ import unicode_literals, print_function

from hashlib import sha256

import importlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile

import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

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

###############
# This block supports builds and manages the content catalog
###############
def _initialize_db( dbfile ):
    conn = sqlite3.connect( dbfile )

    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE records (name TEXT, version INT, builder TEXT, build_time INT, indexer TEXT, index_time INT, archive TEXT, PRIMARY KEY(name, version))''')
    cursor.execute('''CREATE TABLE state (recordId INT, state TEXT, PRIMARY KEY(recordId, state))''')
    conn.commit()

    return conn

def _write_catalog( conn, catalog ):
    cursor = conn.cursor()
    for entry in catalog:
        entry = catalog[entry]
        # Test if the record is already in the DB
        cursor.execute('SELECT COUNT(*) FROM records WHERE name=? and version=?', (entry['name'], int(entry['version'])))
        if int(cursor.fetchone()[0]):
            logger.debug('%s, version %s, is already in the database.' % (entry['name'], entry['version']))
        else:
            cursor.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)', (entry['name'], int(entry['version']), entry['builder'], int(entry['build_time']), entry['indexer'], int(entry['index_time']), entry['archive']))

        cursor.execute('SELECT _rowid_ FROM records WHERE name=? and version=?', (entry['name'], int(entry['version'])))
        row_id = cursor.fetchone()[0]
        for state in entry['state']:
            cursor.execute('SELECT COUNT(*) FROM state WHERE recordId=? and state=?', (row_id, state))
            if int(cursor.fetchone()[0]) == 0:
                cursor.execute('INSERT INTO state VALUES (?,?)', (row_id, state))

    conn.commit()

def _read_catalog( conn ):
    catalog = {}
    cursor = conn.cursor()
    
    # Fetch the records
    cursor.execute('SELECT name, version, builder, build_time, indexer, index_time, archive, _rowid_ FROM records ORDER BY version DESC, name')
    records = cursor.fetchall()
    for record in records:
        key = '-'.join([record[0], unicode(record[1])])
        logger.debug('Read %s from catalog' % (key))
        catalog[key] = {'name': record[0], 'version': record[1], 'builder': record[2], 'build_time': record[3], 'indexer': record[4], 'index_time': record[5], 'archive': record[6], 'state': []}
        cursor.execute('SELECT state FROM state WHERE recordId=?', (record[7],))
        states = cursor.fetchall()
        for state in states:
            catalog[key]['state'].append(state[0])
    return catalog

def _is_content_package( file ):
    return (os.path.isfile(file) and '.tgz' in file)

def _is_valid_file_or_link( filename ):
    return ((os.path.isfile(filename) and not os.path.islink(filename)) or (os.path.islink(filename) and os.path.exists(os.path.join(os.path.dirname(filename), os.readlink(filename)))))

def _build_catalog(conn, content_store):
    logger.info('Building catalog')
    catalog = {}
    for root, dirs, files in os.walk(content_store):
        for file in files:
            content_file = os.path.join(root,file)
            if _is_content_package(content_file) and _is_valid_file_or_link(content_file):
                logger.debug('Processesing %s' % (file,))
                state = os.path.basename(root)
                if os.path.islink(content_file):
                    linkpath = os.readlink(content_file)
                    if not os.path.isabs(linkpath):
                        linkpath = os.path.normpath(os.path.join(os.path.dirname(content_file), linkpath))
                    content_file = linkpath

                records = get_from_catalog(content_store, archive=os.path.relpath(content_file, content_store))
                if records:
                    logger.debug('Using existing record for %s' % (os.path.relpath(content_file, content_store),))
                    record = records[0]
                else:
                    record = get_content_metadata( content_file )
                    record['archive'] = os.path.relpath(content_file, content_store)
                    record['state'] = []

                key = '-'.join([record['name'], record['version']])
                if key not in catalog.keys():
                    catalog[key] = record

                if state not in catalog[key]['state']:
                    logger.debug('Adding state: %s' % state)
                    catalog[key]['state'].append(state)

    _write_catalog(conn, catalog)

    return catalog

def _clean_catalog(conn, content_store):
    logger.info('Cleaning catalog')
    catalog = _read_catalog( conn )
    
    for entry in catalog.values():
        if _is_valid_file_or_link(os.path.join(content_store, entry['archive'])):
            logger.debug('%s is present' % (os.path.join(content_store, entry['archive']),))
            
            base, file = os.path.split(entry['archive'])
            for state in entry['state']:
                if state == base:
                    continue
                if _is_valid_file_or_link(os.path.join(content_store,state, file)):
                    logger.debug('%s exists for %s' % (state, file))
                else:
                    logger.warning('%s missing for %s. Removing.' % (state, file))
                    entry['state'].remove(state)
                    update_catalog(content_store, [entry])

        else:
            logger.warn('%s is missing. We should remove this from the catalog' % (os.path.join(content_store, entry['archive']),))
            cursor = conn.cursor()
            cursor.execute('SELECT _rowid_ FROM records WHERE name=? and version=?', (entry['name'], int(entry['version'])))
            row_id = cursor.fetchone()[0]
            for state in entry['state']:
                cursor.execute('DELETE FROM state WHERE recordId=?', (row_id,))
            cursor.execute('DELETE FROM records WHERE _rowid_=?', (row_id,))
            conn.commit()

def _open_catalog( content_store ):
    if _is_content_package(content_store):
        logger.warn('The content-store is a content package.')
        return

    dbfile = os.path.join(content_store, 'catalog.db')

    conn = None
    existing = True
    if not os.path.exists(dbfile):
        conn = _initialize_db(dbfile)
        existing = False
    else:
        conn = sqlite3.connect(dbfile)

    return (conn, existing)

def get_catalog( content_store ):
    conn, existing = _open_catalog( content_store )

    if existing:
        catalog = _read_catalog(conn)
    else:
        catalog = _build_catalog(conn, content_store)

    return catalog

def get_from_catalog( content_store, title='', version='', archive='' ):
    conn, existing = _open_catalog( content_store )

    if not existing:
        _build_catalog(conn, content_store)

    cursor = conn.cursor()
    if version and title:
        cursor.execute('SELECT name, version, builder, build_time, indexer, index_time, archive, _rowid_  FROM records WHERE name=? AND version=?', (title, version))
    elif version:
        cursor.execute('SELECT name, version, builder, build_time, indexer, index_time, archive, _rowid_  FROM records WHERE version=?', (version,))
    elif title:
        cursor.execute('SELECT name, version, builder, build_time, indexer, index_time, archive, _rowid_  FROM records WHERE name=?', (title,))
    elif archive:
        cursor.execute('SELECT name, version, builder, build_time, indexer, index_time, archive, _rowid_  FROM records WHERE archive=?', (archive,))

    catalog = []
    records = cursor.fetchall()
    for record in records:
        entry = {'name': record[0], 'version': unicode(record[1]), 'builder': record[2], 'build_time': unicode(record[3]), 'indexer': record[4], 'index_time': unicode(record[5]), 'archive': record[6], 'state': []}
        entry['archive'] = os.path.join(content_store, entry['archive'])
        cursor.execute('SELECT state FROM state WHERE recordId=?', (record[7],))
        states = cursor.fetchall()
        for state in states:
            entry['state'].append(state[0])
        catalog.append(entry)

    conn.close()

    return catalog

def get_latest_from_catalog( content_store, category='testing', title='' ):
    conn, existing = _open_catalog( content_store )

    if not existing:
        _build_catalog(conn, content_store)

    cursor = conn.cursor()
    if title:
        cursor.execute('SELECT name, MAX(version), builder, build_time, indexer, index_time, archive  FROM records JOIN state ON records._rowid_ = state.recordId WHERE state=? AND name=? GROUP BY name', (category, title))
    else:
        cursor.execute('SELECT name, MAX(version), builder, build_time, indexer, index_time, archive  FROM records JOIN state ON records._rowid_ = state.recordId WHERE state=? GROUP BY name', (category,))

    catalog = []
    records = cursor.fetchall()
    for record in records:
        entry = {'name': record[0], 'version': unicode(record[1]), 'builder': record[2], 'build_time': unicode(record[3]), 'indexer': record[4], 'index_time': unicode(record[5]), 'archive': record[6], 'state': [category]}
        entry['archive'] = os.path.join(content_store, entry['archive'])
        catalog.append(entry)

    conn.close()

    return catalog

def update_catalog( content_store, content_list):
    conn, existing = _open_catalog( content_store )

    #if not existing:
    #    _build_catalog(conn, content_store)

    cursor = conn.cursor()
    
    for entry in content_list:
        # Determine if the entry is already in the DB.
        cursor.execute('SELECT COUNT(*) FROM records WHERE name=? AND version=?', (entry['name'], int(entry['version'])))
        if int(cursor.fetchone()[0]) == 0:
            logger.info('Adding %s, version %s, to the database.' % (entry['name'], entry['version']))
            archive = os.path.relpath(entry['archive'], content_store)
            cursor.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)', (entry['name'], int(entry['version']), entry['builder'], int(entry['build_time']), entry['indexer'], int(entry['index_time']), archive))
        else:
            logger.info('%s, version %s, is already in the database.' % (entry['name'], entry['version']))

        cursor.execute('SELECT _rowid_ FROM records WHERE name=? AND version=?', (entry['name'], int(entry['version'])))
        row_id = cursor.fetchone()[0]
        for state in entry['state']:
            cursor.execute('SELECT COUNT(*) FROM state WHERE recordId=? AND state=?', (row_id, state))
            if int(cursor.fetchone()[0]) == 0:
                cursor.execute('INSERT INTO state VALUES (?,?)', (row_id, state))
        cursor.execute('SELECT state FROM state WHERE recordId=?', (row_id,))
        states = cursor.fetchall()
        for state in states:
            if state[0] not in entry['state']:
                cursor.execute('DELETE FROM state WHERE recordId=? AND state=?', (row_id, state[0]))

    conn.commit()
    conn.close()

def _get_content( content_store='.', prefix='testing', title='', version='', all_versions=False ):
    """This method retrieves content from the local filesystem content store. 
    The name variable specifies the desired content title. The version 
    variable specifies the desired version of a content title. If name and 
    version are unspecified then it will retrieve the latest content package 
    for each content title found in the local store.
    NOTE: Does not yet return all mathcing content when requested."""

    # Determine if we are getting the latest content or a particular version
    content_list = []
    if version is '':
        content_list = get_latest_from_catalog( content_store, category=prefix, title=title )
    else:
        content_list = get_from_catalog( content_store, title=title, version=version )

    return content_list

def get_content( config=None, prefix='testing', title='', version='', all_versions=False ):
    """Public method used to retrive content and most abstract away the 
    differences in fetching content from S3 and a local content store."""

    if not config:
        raise Exception("Must pass a config object")

    print('Determining the latest content. This may take a (really) long time.')

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
            if not hasattr(content, 'state'):
                content['state'] = []
            content['state'].append(dest);
    update_catalog(config['content-store'], content_list)

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
