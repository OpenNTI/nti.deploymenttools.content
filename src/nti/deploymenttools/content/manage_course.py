#!/usr/bin/env python

import logging
import os

from argparse import ArgumentParser
from getpass import getpass
from shutil import copy2
from shutil import rmtree
from tempfile import mkdtemp
from six.moves.urllib.parse import unquote
from zipfile import ZipFile

import requests
import simplejson as json

from nti.deploymenttools.content import archive_directory
from nti.deploymenttools.content import configure_logging
from nti.deploymenttools.content import export_course
from nti.deploymenttools.content import import_course
from nti.deploymenttools.content import restore_course

logger = __import__('logging').getLogger(__name__)
logging.captureWarnings(True)

requests_codes = requests.codes

UA_STRING = 'NextThought Course Management Utility'

def _remove_path(path):
    if path and os.path.exists(path):
        rmtree(path)

def get_course_catalog_entry(course_ntiid, host, username, password,
                             ua_string):
    url = 'https://%s/dataserver2/Objects/%s/' % (host, course_ntiid)
    headers = {
        'user-agent': ua_string
    }

    response = requests.get(url, headers=headers, auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests_codes.ok:
        return response.json()

def get_course_instance(course_ntiid, host, username, password, ua_string):
    headers = {
        'user-agent': ua_string
    }

    course_catalog_entry = get_course_catalog_entry(course_ntiid, host,
                                                    username, password,
                                                    ua_string)
    url = None
    for link in course_catalog_entry['Links']:
        if link['rel'] == 'CourseInstance':
            url = 'https://%s%s' % (host,link['href'])

    response = requests.get(url, headers=headers, auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests_codes.ok:
        return response.json()

def _get_course_tuple(course_catalog_entry):
    href = course_catalog_entry['href'].split('/')
    site_library = unquote(href[3])
    admin_level = unquote(href[6])
    provider_id = unquote(href[7])
    return site_library, admin_level, provider_id

def _is_duplicate_discussion(host, username, password, course_instance,
                             discussion, ua_string):
    headers = {
        'user-agent': ua_string
    }

    url = None
    for link in course_instance['Links']:
        if link['rel'] == 'CourseDiscussions':
            url = 'https://%s%s' % (host,link['href'])

    response = requests.get(url, headers=headers, auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests_codes.ok:
        course_discussions = response.json()
        for course_discussion in course_discussions['Items']:
            if discussion['title'] == course_discussion['title']:
                for key in discussion:
                    if discussion[key] != course_discussion[key]:
                        return False
                return True
    return False

def register_discussion(course_ntiid, host, username, password,
                        discussion_path, ua_string):
    headers = {
        'Content-Type': 'application/json',
        'user-agent': ua_string,
        'X-Requested-With': 'XMLHttpRequest'
    }

    course_instance = get_course_instance(course_ntiid, host, username,
                                          password, ua_string)
    url = None
    for link in course_instance['Links']:
        if link['rel'] == 'CourseDiscussions':
            url = 'https://%s%s' % (host,link['href'])
    try:
        with open(os.path.abspath(os.path.expanduser(discussion_path)), 'rb') as fp:
            discussion = json.load(fp)
            if not _is_duplicate_discussion(host, username, password,
                                            course_instance, discussion,
                                            ua_string):
                logger.debug(json.dumps(discussion))
                response = requests.post(url, headers=headers,
                                         data=json.dumps(discussion),
                                         auth=(username, password))
                response.raise_for_status()
                if response.status_code == requests_codes.created:
                    logger.debug(json.dumps(response.json()))
                    return response.json()
            else:
                logger.info('Discussion %s is a duplicate.',
                            discussion['title'])
    except requests.exceptions.HTTPError as e:
        logger.error(e)

def create_discussions(course_ntiid, host, username, password,
                       discussion_paths, ua_string):
    course_instance = get_course_instance(course_ntiid, host, username,
                                          password, ua_string)
    url = 'https://%s%s/@@CreateDiscussionTopics' % (host,course_instance['href'])
    headers = {
        'user-agent': ua_string
    }

    for discussion_path in discussion_paths:
        discussion = register_discussion(course_ntiid, host, username,
                                         password, discussion_path, ua_string)
        if discussion:
            response = requests.post(url, headers=headers,
                                     auth=(username, password))
            response.raise_for_status()
            if response.status_code == requests_codes.ok:
                logger.info(json.dumps(response.json()))
            else:
                logger.info(response.status_code)

def _update_course_archive(course_archive, **kwargs):
    temp_dir = mkdtemp()

    modified_course_archive = os.path.splitext(course_archive)
    modified_course_archive = modified_course_archive[0] + \
        '_modified' + modified_course_archive[1]
    try:
        with ZipFile(course_archive, 'r') as archive:
            for name in archive.namelist():
                archive.extract(name, temp_dir)

        for key in kwargs:
            if key == 'asset_path':
                logger.debug('Clearing old presentation assets')
                _remove_path(os.path.join(temp_dir,'presentation-assets'))
            if key == 'discussion_paths':
                discussion_dir = os.path.join(temp_dir, 'Discussions')
                if not os.path.exists(discussion_dir):
                    os.mkdir(discussion_dir)
                for path in kwargs[key]:
                    logger.debug('Copying %s to %s', path, discussion_dir)
                    copy2(path, discussion_dir)
            if key == 'metadata_path':
                metadata_path = kwargs[key]
                for path in ['bundle_dc_metadata.xml', 'dc_metadata.xml']:
                    logger.debug('Copying %s to %s', metadata_path,
                                 os.path.join(temp_dir, path))
                    copy2(metadata_path,os.path.join(temp_dir, path))
            if key == 'vendor_path':
                vendor_path = kwargs[key]
                logger.debug('Copying %s to %s', vendor_path, temp_dir)
                copy2(vendor_path,temp_dir)

        archive_directory(temp_dir, modified_course_archive)
    finally:
        _remove_path(temp_dir)

    with ZipFile(modified_course_archive, 'a') as archive:
        for key in kwargs:
            if key == 'asset_path':
                asset_path = kwargs[key] + '/'
                logger.debug('Adding presentation assets from %s', asset_path)
                for root, _, files in os.walk(asset_path):
                    for source in files or ():
                        file_path = os.path.join(root, source)
                        archive_file_path = file_path.replace(asset_path, '', 1)
                        archive_file_path = os.path.join('presentation-assets',
                                                     archive_file_path)
                        logger.debug('Adding %s to the archive as %s.' %
                                     (file_path, archive_file_path))
                        archive.write(file_path, archive_file_path)

    return modified_course_archive

def update_course(host, username, password, course_ntiid, ua_string, **kwargs):
    cwd = os.getcwd()
    working_dir = mkdtemp()
    try:
        os.chdir(working_dir)
        course_archive = export_course(course_ntiid, host, username,
                                       password, UA_STRING, backup=True)
        course_archive = _update_course_archive(course_archive, **kwargs)

        course_catalog_entry = get_course_catalog_entry(course_ntiid, host,
                                                        username, password,
                                                        UA_STRING)
        site_library, admin_level, provider_id = _get_course_tuple(course_catalog_entry)
        import_course(course_archive, host, username, password, site_library,
                      admin_level, provider_id, ua_string)
    finally:
        _remove_path(working_dir)

def _parse_args():
    arg_parser = ArgumentParser( description=UA_STRING )
    arg_parser.add_argument('-v', '--verbose', dest='loglevel',
                            action='store_const', const=logging.DEBUG,
                            help="Print debugging logs.")
    arg_parser.add_argument('-q', '--quiet', dest='loglevel',
                            action='store_const', const=logging.WARNING,
                            help="Print warning and error logs only.")

    subparsers =  arg_parser.add_subparsers(dest='subparser_name')

    dcmetadata_parser = subparsers.add_parser('dcmetadata',
                            description='Dublin Core Metadata Management')
    dcmetadata_parser.add_argument('-n', '--ntiid', dest='ntiid',
                                   help="NTIID of the course.")
    dcmetadata_parser.add_argument('-s', '--server', dest='host',
                                   help="Server to connect to.")
    dcmetadata_parser.add_argument('-u', '--user', dest='user',
                                   help="User to authenticate with the server.")
    dcmetadata_parser.add_argument('-f', '--file', dest='file',
                                   help="New dc metadata info file to upload.")

    discussion_parser = subparsers.add_parser('discussions',
                            description='Discussion Management')
    discussion_parser.add_argument('-n', '--ntiid', dest='ntiid',
                                   help="NTIID of the course.")
    discussion_parser.add_argument('-s', '--server', dest='host',
                                   help="Server to connect to.")
    discussion_parser.add_argument('-u', '--user', dest='user',
                                   help="User to authenticate with the server.")
    discussion_parser.add_argument('-a', '--add', dest='discussions',
                                   nargs='*', help="Discussions to add.")

    presentation_parser = subparsers.add_parser('presentationassets',
                            description='Presentation Asset Management')
    presentation_parser.add_argument('-n', '--ntiid', dest='ntiid',
                                     help="NTIID of the course.")
    presentation_parser.add_argument('-s', '--server', dest='host',
                                     help="Server to connect to.")
    presentation_parser.add_argument('-u', '--user', dest='user',
                                     help="User to authenticate with the server.")
    presentation_parser.add_argument('-f', '--file', dest='file',
                                     help="Path to new presentation assets.")

    vendorinfo_parser = subparsers.add_parser('vendorinfo',
                            description='Vendor Info Management')
    vendorinfo_parser.add_argument('-n', '--ntiid', dest='ntiid',
                                   help="NTIID of the course.")
    vendorinfo_parser.add_argument('-s', '--server', dest='host',
                                   help="Server to connect to.")
    vendorinfo_parser.add_argument('-u', '--user', dest='user',
                                   help="User to authenticate with the server.")
    vendorinfo_parser.add_argument('-f', '--file', dest='file',
                                   help="New vendor info file to upload.")

    return arg_parser.parse_args()

def main():
    # Parse command line args
    args = _parse_args()

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    if args.subparser_name == 'dcmetadata':
        if args.file:
            try:
                metadata_path = os.path.abspath(os.path.expanduser(args.file))
                password = getpass('Password for %s@%s: ' % (args.user, args.host))
                update_course(args.host, args.user, password, args.ntiid,
                              UA_STRING, metadata_path=metadata_path)
            except requests.exceptions.HTTPError as e:
                logger.error(e)
    elif args.subparser_name == 'discussions':
        if args.discussions:
            try:
                discussions = []
                for path in args.discussions:
                    discussions.append(os.path.abspath(os.path.expanduser(path)))
                password = getpass('Password for %s@%s: ' % (args.user, args.host))
                update_course(args.host, args.user, password, args.ntiid,
                              UA_STRING, discussion_paths=discussions)
            except requests.exceptions.HTTPError as e:
                logger.error(e)
    elif args.subparser_name == 'presentationassets':
        if args.file:
            try:
                asset_path = os.path.abspath(os.path.expanduser(args.file))
                password = getpass('Password for %s@%s: ' % (args.user, args.host))
                update_course(args.host, args.user, password, args.ntiid,
                              UA_STRING, asset_path=asset_path)
            except requests.exceptions.HTTPError as e:
                logger.error(e)
    elif args.subparser_name == 'vendorinfo':
        if args.file:
            try:
                vendor_path = os.path.abspath(os.path.expanduser(args.file))
                password = getpass('Password for %s@%s: ' % (args.user, args.host))
                update_course(args.host, args.user, password, args.ntiid,
                              UA_STRING, vendor_path=vendor_path)
            except requests.exceptions.HTTPError as e:
                logger.error(e)

if __name__ == '__main__': # pragma: no cover
        main()
