#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import getpass
import logging
import argparse

from nti.deploymenttools.content import restore_course
from nti.deploymenttools.content import configure_logging

logger = __import__('logging').getLogger(__name__)

UA_STRING = 'NextThought Course Restore Utility'


def _parse_args(args=None):
    arg_parser = argparse.ArgumentParser(description=UA_STRING)
    arg_parser.add_argument('coursepath', help="Course archive to restore")
    arg_parser.add_argument('-n', '--ntiid', dest='ntiid',
                            help="NTIID of the course to restore.")
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
    return arg_parser.parse_args(args)


def main(args=None):
    args = _parse_args(args)

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    archive = os.path.abspath(os.path.expanduser(args.coursepath))
    if not os.path.exists(archive) or not os.path.isfile(archive):
        raise IOError("Invalid course archive")

    msg = 'Password for %s@%s:' % (args.user, args.dest_host)
    password = getpass.getpass(msg)

    logger.info("Restoring course from %s to %s",
                archive, args.dest_host)

    course = restore_course(archive,
                            args.dest_host,
                            args.user,
                            password,
                            args.ntiid,
                            UA_STRING)

    logger.info('Course restored sucessfully as %s.',
                course['Course']['NTIID'])


if __name__ == '__main__':  # pragma: no cover
    main()
