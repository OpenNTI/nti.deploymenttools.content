#!/usr/bin/env python

from argparse import ArgumentParser
from getpass import getpass

from nti.deploymenttools.content import configure_logging
from nti.deploymenttools.content import export_course

import logging
import requests

logger = logging.getLogger('nti_backup_course')
logging.captureWarnings(True)

UA_STRING = 'NextThought Course Backup Utility'

def backup_course(course_ntiid, source_host, username, cleanup=True):
    course_archive = None
    try:
        password = getpass('Password for %s@%s: ' % (username, source_host))
        logger.info("Backing up %s from %s" % (course_ntiid, source_host))
        course_archive = export_course( course_ntiid, source_host, username, password, UA_STRING, backup=True )
        logger.info('Course %s backed up at %s.' % (course_ntiid,course_archive))

    except requests.exceptions.HTTPError as e:
        logger.error(e)

def _parse_args():
    arg_parser = ArgumentParser( description=UA_STRING )
    arg_parser.add_argument( '-n', '--ntiid', dest='ntiid',
                             help="NTIID of the course to copy." )
    arg_parser.add_argument( '-s', '--source-server', dest='source_host',
                             help="Source server." )
    arg_parser.add_argument( '-u', '--user', dest='user',
                             help="User to authenticate with the server." )
    arg_parser.add_argument( '-v', '--verbose', dest='loglevel', action='store_const', const=logging.DEBUG,
                             help="Print debugging logs." )
    arg_parser.add_argument( '-q', '--quiet', dest='loglevel', action='store_const', const=logging.WARNING,
                             help="Print warning and error logs only." )
    arg_parser.add_argument( '--no-cleanup', dest='no_cleanup', action='store_false', default=True,
                             help="Do not cleanup process files." )
    return arg_parser.parse_args()

def main():
    # Parse command line args
    args = _parse_args()

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    backup_course( args.ntiid,
                 args.source_host,
                 args.user,
                 cleanup=args.no_cleanup )

if __name__ == '__main__': # pragma: no cover
        main()
