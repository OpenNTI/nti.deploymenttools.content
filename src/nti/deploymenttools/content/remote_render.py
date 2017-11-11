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
from time import sleep
from shutil import rmtree
from getpass import getpass
from tempfile import mkdtemp
from argparse import ArgumentParser

import requests

from nti.deploymenttools.content import archive_directory
from nti.deploymenttools.content import configure_logging

UA_STRING = 'NextThought Remote Render Utility'

logger = __import__('logging').getLogger(__name__)
logging.captureWarnings(True)

requests_codes = requests.codes


def _remove_path(path):
    if path and os.path.exists(path):
        rmtree(path)


def remote_render(host, user, password, site_library, working_dir,
                  poll_interval, cleanup=True):

    def _get_job_name(working_dir):
        for source in os.listdir(working_dir):
            base_name, ext = os.path.splitext(os.path.basename(source))
            if ext == '.tex':
                logger.debug('Using %s as the job name.', base_name)
                return base_name
        return 'unknown'

    def _build_archive(working_dir, temp_dir):
        job_name = _get_job_name(working_dir)
        archive_path = os.path.join(temp_dir, job_name + '.zip')
        archive_directory(working_dir, archive_path)
        return archive_path, job_name

    def _monitor_job(response, host, user, password, poll_interval):
        response_body = response.json()
        for link in response_body['Items'][job_name + '.zip']['Links']:
            if link['rel'] == 'error':
                error_link = 'https://%s' % host + link['href']
            elif link['rel'] == 'status':
                status_link = 'https://%s' % host + link['href']

        logger.info('Render job %s submitted.',
                    response_body['Items'][job_name + '.zip']['JobId'])

        response = requests.get(status_link, headers=headers,
                                auth=(user, password))
        response.raise_for_status()
        status = response.json()['status']
        while status in ('Pending', 'Running'):
            logger.info("Render is %s", status)
            sleep(poll_interval)
            response = requests.get(status_link, headers=headers,
                                    auth=(user, password))
            response.raise_for_status()
            status = response.json()['status']
        if status == 'Failed':
            response = requests.get(error_link, headers=headers,
                                    auth=(user, password))
            response.raise_for_status()
            logger.error('Render failed.\n%s', response.json()['message'])
        elif status == 'Success':
            logger.info('Render succeeded.')

    url = 'https://%s/dataserver2/Library/@@RenderContentSource' % host
    headers = {
        'user-agent': UA_STRING
    }

    logger.info('Submitting render of %s to %s' % (working_dir, host))
    try:
        temp_dir = mkdtemp()
        logger.info('Using %s to store temporary files' % (temp_dir,))
        content_archive, job_name = _build_archive(working_dir, temp_dir)

        files = {job_name: open(content_archive, 'rb')}
        data = {'site': site_library}

        response = requests.post(url, headers=headers,
                                 files=files, data=data,
                                 auth=(user, password))
        response.raise_for_status()

        if response.status_code == requests_codes.ok:
            _monitor_job(response, host, user, password, poll_interval)

    except requests.HTTPError:
        logger.exception("Request HTTP error")
    except requests.exceptions.ReadTimeout:
        logger.warning('No response from %s while attempting to render %s.',
                       host, working_dir)
    finally:
        if cleanup:
            _remove_path(temp_dir)


def _parse_args():
    arg_parser = ArgumentParser(description="Remote Rendering Utility")
    arg_parser.add_argument('contentpath',
                            help="Directory containing the content")
    arg_parser.add_argument('-s', '--server', dest='host',
                            help="The remote rendering server.")
    arg_parser.add_argument('-u', '--user', dest='user',
                            help="User to authenticate with the server.")
    arg_parser.add_argument('--site-library', dest='site_library',
                            help="Site library to add content to. Defaults to the hostname of the destination server.")
    arg_parser.add_argument('-v', '--verbose', dest='loglevel',
                            action='store_const', const=logging.DEBUG,
                            help="Print debugging logs.")
    arg_parser.add_argument('-q', '--quiet', dest='loglevel', action='store_const',
                            const=logging.WARNING,
                            help="Print warning and error logs only.")
    arg_parser.add_argument('--poll-interval', dest='poll_interval', default=10, type=int,
                            help="Seconds between render status checks. Defaults to 10 seconds.")
    arg_parser.add_argument('--no-cleanup', dest='cleanup', action='store_false',
                            default=True,
                            help="Do not cleanup process files.")
    return arg_parser.parse_args()


def main():
    args = _parse_args()

    site_library = args.site_library or args.host

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    password = getpass('Password for %s@%s: ' % (args.user, args.host))
    working_dir = os.path.abspath(os.path.expanduser(args.contentpath))
    if os.path.isfile(working_dir):
        working_dir = os.path.dirname(working_dir)
    logger.info(working_dir)

    remote_render(args.host, args.user, password, site_library,
                  working_dir, args.poll_interval, cleanup=args.cleanup)


if __name__ == '__main__':  # pragma: no cover
    main()
