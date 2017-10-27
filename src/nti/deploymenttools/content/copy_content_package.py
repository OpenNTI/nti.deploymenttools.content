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
from getpass import getpass
from argparse import ArgumentParser

from requests import exceptions as requests_exceptions

from nti.deploymenttools.content import configure_logging
from nti.deploymenttools.content import download_rendered_content
from nti.deploymenttools.content import upload_rendered_content

UA_STRING = 'NextThought Content Package Copy Utility'

logger = __import__('logging').getLogger(__name__)
logging.captureWarnings(True)


def _remove_path(path):
    if path and os.path.exists(path):
        os.remove(path)


def copy_content_package(content_ntiid, source_host, dest_host, username,
                         site_library, cleanup=True):
    content_archive = None
    try:
        logger.info("Downloading content package from %s", source_host)
        password = getpass('Password for %s@%s: ' % (username, source_host))
        content_archive = download_rendered_content(content_ntiid, source_host,
                                                    username, password, UA_STRING)

        logger.info("Uploading content package to %s", dest_host)
        password = getpass('Password for %s@%s: ' % (username, dest_host))
        content = upload_rendered_content(content_archive, dest_host,
                                          username, password, site_library, UA_STRING)
        logger.info('Successfully uploaded as %s',
                    list(content['Items'].keys())[0])
    except requests_exceptions.HTTPError as e:
        logger.error(e)
    finally:
        if cleanup:
            _remove_path(content_archive)


def _parse_args():
    arg_parser = ArgumentParser(description=UA_STRING)
    arg_parser.add_argument('-n', '--ntiid', dest='content_ntiid',
                            help="NTIID of content to copy.")
    arg_parser.add_argument('-s', '--source-server', dest='source_host',
                            help="Source server.")
    arg_parser.add_argument('-d', '--dest-server', dest='dest_host',
                            help="Destination server.")
    arg_parser.add_argument('-u', '--user', dest='user',
                            help="User to authenticate with the server.")
    arg_parser.add_argument('--site-library', dest='site_library',
                            help="Site library to add content to. Defaults to the hostname of the destination server.")
    arg_parser.add_argument('-v', '--verbose', dest='loglevel', action='store_const',
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

    site_library = args.site_library or args.dest_host

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    copy_content_package(args.content_ntiid, args.source_host,
                         args.dest_host, args.user, site_library,
                         cleanup=args.no_cleanup)


if __name__ == '__main__':  # pragma: no cover
    main()
