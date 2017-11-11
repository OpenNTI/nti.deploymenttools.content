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

import requests

from nti.deploymenttools.content import import_course
from nti.deploymenttools.content import configure_logging

UA_STRING = 'NextThought Course Import Utility'

logger = __import__('logging').getLogger(__name__)
logging.captureWarnings(True)


def _parse_args():
    arg_parser = ArgumentParser(description=UA_STRING)
    arg_parser.add_argument('coursepath', help="Course archive to import")
    arg_parser.add_argument('-d', '--dest-server', dest='dest_host',
                            help="Destination server.")
    arg_parser.add_argument('-u', '--user', dest='user',
                            help="User to authenticate with the server.")
    arg_parser.add_argument('-a', '--admin-level', dest='admin_level', default='DefaultAPIRestored',
                            help="Specifies the organizational admin level for the course.")
    arg_parser.add_argument('-p', '--provider-id', dest='provider_id',
                            help="Custom provider id for the copied course.")
    arg_parser.add_argument('--site-library', dest='site_library',
                            help="Site library to add content to. Defaults to the hostname of the destination server.")
    arg_parser.add_argument('-v', '--verbose', dest='loglevel', action='store_const', const=logging.DEBUG,
                            help="Print debugging logs.")
    arg_parser.add_argument('-q', '--quiet', dest='loglevel', action='store_const', const=logging.WARNING,
                            help="Print warning and error logs only.")
    return arg_parser.parse_args()


def main():
    # Parse command line args
    args = _parse_args()
    course_archive = os.path.abspath(os.path.expanduser(args.coursepath))

    site_library = args.site_library or args.dest_host

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    try:
        password = getpass('Password for %s@%s: ' %
                           (args.user, args.dest_host))
        logger.info("Importing course from %s to %s",
                    course_archive, args.dest_host)
        course = import_course(course_archive, args.dest_host, args.user,
                               password, site_library, args.admin_level,
                               args.provider_id, UA_STRING)
        logger.info('Course imported sucessfully as %s.' %
                    (course['Course']['NTIID'],))

    except requests.exceptions.HTTPError as e:
        logger.error(e)


if __name__ == '__main__':  # pragma: no cover
    main()
