#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import logging
from shutil import rmtree
from getpass import getpass
from zipfile import ZipFile
from tempfile import mkdtemp
from argparse import ArgumentParser

import requests

import simplejson as json

from isodate import parse_datetime
from isodate import datetime_isoformat

from nti.deploymenttools.content import export_course
from nti.deploymenttools.content import import_course
from nti.deploymenttools.content import archive_directory
from nti.deploymenttools.content import configure_logging
from nti.deploymenttools.content import upload_rendered_content
from nti.deploymenttools.content import download_rendered_content

UA_STRING = 'NextThought Course Copy Utility'

logger = __import__('logging').getLogger(__name__)


def _get_content_packages(course_archive):
    with ZipFile(course_archive, 'r') as archive:
        bundle_metadata = json.load(archive.open('bundle_meta_info.json'))
        content_packages = bundle_metadata['ContentPackages']
    return content_packages or ()


def _get_provider_id(course_archive):
    with ZipFile(course_archive, 'r') as archive:
        course_info = json.load(archive.open('course_info.json'))
        provider_id = course_info['id']
    return provider_id


def _remove_path(path):
    if path and os.path.exists(path):
        rmtree(path)


def _update_course_archive(course_archive, provider_id, start_date, end_date):
    temp_dir = mkdtemp()

    modified_course_archive = os.path.splitext(course_archive)
    modified_course_archive = modified_course_archive[0] + \
        '_modified' + modified_course_archive[1]
    try:
        with ZipFile(course_archive, 'r') as archive:
            for name in archive.namelist():
                archive.extract(name, temp_dir)

        course_info = {}
        with open(os.path.join(temp_dir, 'course_info.json'), 'r') as fp:
            course_info = json.load(fp)

            if provider_id:
                course_info['id'] = provider_id

            if start_date:
                start_date = parse_datetime(start_date)
                course_info['startDate'] = datetime_isoformat(start_date)

            if end_date:
                end_date = parse_datetime(end_date)
                course_info['endDate'] = datetime_isoformat(end_date)

        with open(os.path.join(temp_dir, 'course_info.json'), 'w') as fp:
            json.dump(course_info, fp)

        archive_directory(temp_dir, modified_course_archive)
    finally:
        _remove_path(temp_dir)
    return modified_course_archive


def copy_course(course_ntiid, source_host, dest_host, username, site_library,
                admin_level, provider_id=None, start_date=None, end_date=None, cleanup=True):
    cwd = os.getcwd()
    course_archive = None
    content_archives = []
    working_dir = mkdtemp()
    try:
        os.chdir(working_dir)
        logger.info('Using %s as the working directory', working_dir)
        password = getpass('Password for %s@%s: ' % (username, source_host))
        logger.info("Exporting %s from %s", course_ntiid, source_host)
        course_archive = export_course(course_ntiid, source_host,
                                       username, password, UA_STRING)
        if source_host != dest_host:
            for content_package in _get_content_packages(course_archive):
                logger.info("Downloading content package %s", content_package)
                content_archive = download_rendered_content(content_package, source_host,
                                                            username, password, UA_STRING)
                content_archives.append((content_package, content_archive))

            password = getpass('Password for %s@%s: ' % (username, dest_host))

            for content_archive in content_archives:
                logger.info("Uploading content package %s", content_archive[0])
                upload_rendered_content(content_archive[1], dest_host,
                                        username, password, site_library, UA_STRING)

        # Update course metadata with supplied information
        provider_id = provider_id or _get_provider_id(course_archive)
        course_archive = _update_course_archive(course_archive, provider_id,
                                                start_date, end_date)

        # TODO: Check if admin level exists on dest server, if not, create it.
        logger.info("Importing %s to %s", course_ntiid, dest_host)
        course = import_course(course_archive, dest_host, username,
                               password, site_library, admin_level, provider_id, UA_STRING)
        logger.info('Course imported sucessfully as %s.',
                    course['Course']['NTIID'])

    except requests.exceptions.HTTPError as e:
        logger.error(e)
    finally:
        os.chdir(cwd)
        if cleanup:
            _remove_path(working_dir)


def _parse_args(args=None):
    arg_parser = ArgumentParser(description=UA_STRING)
    arg_parser.add_argument('-n', '--ntiid', dest='ntiid',
                            help="NTIID of the course to copy.")
    arg_parser.add_argument('-s', '--source-server', dest='source_host',
                            help="Source server.")
    arg_parser.add_argument('-d', '--dest-server', dest='dest_host',
                            help="Destination server.")
    arg_parser.add_argument('-u', '--user', dest='user',
                            help="User to authenticate with the server.")
    arg_parser.add_argument('-a', '--admin-level', dest='admin_level',
                            default='DefaultAPICopied',
                            help="Specifies the organizational admin level for the course.")
    arg_parser.add_argument('-p', '--provider-id', dest='provider_id',
                            help="Custom provider id for the copied course.")
    arg_parser.add_argument('--start-date', dest='start_date',
                            help="Start date for the copied course.")
    arg_parser.add_argument('--end-date', dest='end_date',
                            help="End date for the copied course.")
    arg_parser.add_argument('--site-library', dest='site_library',
                            help="Site library to add content to. Defaults to the hostname of the destination server.")
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
    return arg_parser.parse_args(args)


def main(args=None):
    args = _parse_args(args)

    site_library = args.site_library or args.dest_host

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    copy_course(args.ntiid,
                args.source_host,
                args.dest_host,
                args.user,
                site_library,
                args.admin_level,
                provider_id=args.provider_id,
                start_date=args.start_date,
                end_date=args.end_date,
                cleanup=args.no_cleanup)


if __name__ == '__main__':  # pragma: no cover
    main()
