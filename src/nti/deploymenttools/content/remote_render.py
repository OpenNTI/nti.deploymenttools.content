#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from argparse import ArgumentParser
from getpass import getpass
from tempfile import mkdtemp
from time import time
from zipfile import ZipFile

import json
import os
import requests
import shutil

import logging
logger = logging.getLogger('nti_remote_render')
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
log_handler.setLevel(logging.INFO)
logger.addHandler(log_handler)
logging.captureWarnings(True)

UA_STRING = 'NextThought Remote Render Utility'

def remote_render(host, user, password, working_dir, timeout=1200.0):
    def _build_archive(working_dir, temp_dir):
        def _get_job_name(working_dir):
            for file in os.listdir(working_dir):
                base_name, ext = os.path.splitext(os.path.basename(file))
                if ext == '.tex':
                    logger.debug('Using %s as the job name.' % (base_name,))
                    return base_name
            return 'unknown'

        job_name = _get_job_name(working_dir)
        archive_path = os.path.join(temp_dir, job_name + '.zip')
        base_path = os.path.dirname(working_dir) + os.sep
        with ZipFile(archive_path, 'w') as archive:
            logger.debug('Creating archive %s' % (archive_path,))
            for root, dirs, files in os.walk(working_dir):
                for file in files:
                    file_path = os.path.join(root,file)
                    logger.debug('Adding %s to the archive.' % (file_path,))
                    archive_file_path = file_path.replace(base_path,'')
                    archive.write(file_path, archive_file_path)
        return archive_path, job_name

    url = 'https://%s/dataserver2/Library/@@RenderContentSource' % host
    headers = {
        'user-agent': UA_STRING
    }

    logger.info('Submitting render of %s to %s' % (working_dir, host))
    try:
        temp_dir = mkdtemp()
        content_archive, job_name = _build_archive(working_dir, temp_dir)

        files = {job_name: open(content_archive, 'rb')}

        response = requests.post(url, headers=headers, files=files, auth=(user, password), timeout=timeout)
        response.raise_for_status()
        if response.status_code == requests.codes.ok:
            logger.info('Render of %s succeeded.' % working_dir)
    except requests.HTTPError:
        logger.error(response.text)
    except requests.exceptions.ReadTimeout as e:
        logger.warning('No response from %s in %s seconds while attempting to render %s.' % (host, timeout, working_dir))
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def _parse_args():
    # Parse command line args
    arg_parser = ArgumentParser( description="Remote Rendering Utility" )
    arg_parser.add_argument( 'contentpath', help="Directory containing the content" )
    arg_parser.add_argument( '-s', '--server', dest='host',
                             help="The remote rendering server." )
    arg_parser.add_argument( '-u', '--user', dest='user',
                             help="User to authenticate with the server." )
    arg_parser.add_argument( '-v', '--verbose', dest='verbose', action='store_true', default=False,
                             help="Print debugging logs." )
    arg_parser.add_argument( '-t', '--timeout', dest='timeout', default=1200.0,
                             help="Connection timeout." )
    return arg_parser.parse_args()

def main():
    args = _parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        log_handler.setLevel(logging.DEBUG)

    password = getpass('Password for %s: ' % args.user)
    working_dir = os.path.abspath(os.path.expanduser(args.contentpath))

    remote_render(args.host, args.user, password, working_dir, timeout=float(args.timeout))

if __name__ == '__main__': # pragma: no cover
        main()
