#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import codecs
import os
import logging
from shutil import rmtree
from getpass import getpass
from zipfile import ZipFile
from tempfile import mkdtemp
from argparse import ArgumentParser

import requests

import simplejson as json

from nti.deploymenttools.content import export_course
from nti.deploymenttools.content import get_course_info
from nti.deploymenttools.content import archive_directory
from nti.deploymenttools.content import configure_logging
from nti.deploymenttools.content import download_rendered_content

logger = __import__('logging').getLogger(__name__)
logging.captureWarnings(True)

UA_STRING = 'NextThought Course Copy Utility'


def _get_content_packages(course_archive):
    with ZipFile(course_archive, 'r') as archive:
        bundle_metadata = json.load(archive.open('bundle_meta_info.json'))
        content_packages = bundle_metadata['ContentPackages']
    return content_packages or ()

def _remove_path(path):
    if path and os.path.exists(path):
        rmtree(path)

def _extract_archive(archive, location):
    with ZipFile(archive, 'r') as zip:
        for name in zip.namelist():
            zip.extract(name, location)

def backup_course(course_ntiid, source_host, username, output_dir,
                cleanup=True):
    cwd = os.getcwd()
    course_archive = None
    content_archives = []
    working_dir = mkdtemp()
    staging_dir = mkdtemp()
    try:
        os.chdir(working_dir)
        logger.info('Using %s as the working directory', working_dir)
        password = getpass('Password for %s@%s: ' % (username, source_host))
        logger.info("Exporting %s from %s", course_ntiid, source_host)
        course_info = get_course_info(course_ntiid, source_host,
                                      username, password, UA_STRING)
        admin_level = course_info['AdminLevel']
        provider_id = course_info['ProviderUniqueID']
        course_title = course_info['title']
        course_archive = export_course(course_ntiid, source_host,
                                       username, password, UA_STRING)
        staging_dir = os.path.join(staging_dir, provider_id)
        logger.info("Unzipping course bundle %s", course_archive)
        course_path = os.path.join(staging_dir,"course")
        _extract_archive(course_archive, course_path)

        for content_package in _get_content_packages(course_archive):
            logger.info("Downloading content package %s", content_package)
            content_archive = download_rendered_content(content_package, source_host,
                                                        username, password, UA_STRING)
            content_archives.append((content_package, content_archive))

        for content_archive in content_archives:
            logger.info("Unzipping content package %s", content_archive[0])
            content_path = os.path.join(staging_dir,"content",content_archive[0])
            _extract_archive(content_archive[1], content_path)

        archive_path = os.path.join(admin_level, '.'.join([provider_id,'zip']))
        index_info = '"{0}", "{1}", "{2}"'.format(provider_id, course_title, archive_path)
        index_file = os.path.join(staging_dir, '.'.join([provider_id,'csv']))

        with codecs.open(index_file, 'wb', 'utf-8') as fp:
            fp.write(index_info)

        out_file = os.path.join(output_dir, archive_path)
        if not os.path.exists(os.path.dirname(out_file)):
            os.makedirs(os.path.dirname(out_file))

        archive_directory(os.path.dirname(staging_dir), out_file)

    except requests.exceptions.HTTPError as e:
        logger.error(e)
    finally:
        os.chdir(cwd)
        if cleanup:
            _remove_path(working_dir)
            _remove_path(staging_dir)


def _parse_args():
    arg_parser = ArgumentParser(description=UA_STRING)
    arg_parser.add_argument('-n', '--ntiid', dest='ntiid',
                            help="NTIID of the course to copy.")
    arg_parser.add_argument('-s', '--source-server', dest='source_host',
                            help="Source server.")
    arg_parser.add_argument('-u', '--user', dest='user',
                            help="User to authenticate with the server.")
    arg_parser.add_argument('-o', '--output', dest='output',
                            help="Backup output location.")
    arg_parser.add_argument('-v', '--verbose', dest='loglevel',
                            action='store_const',
                            const=logging.DEBUG,
                            help="Print debugging logs.")
    arg_parser.add_argument('-q', '--quiet', dest='loglevel', action='store_const',
                            const=logging.WARNING,
                            help="Print warning and error logs only.")
    arg_parser.add_argument('--no-cleanup', dest='no_cleanup', action='store_false',
                            default=True,
                            help="Do not cleanup process files.")
    return arg_parser.parse_args()


def main():
    # Parse command line args
    args = _parse_args()

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    backup_course(args.ntiid,
                args.source_host,
                args.user,
                args.output,
                cleanup=args.no_cleanup)


if __name__ == '__main__':  # pragma: no cover
    main()
