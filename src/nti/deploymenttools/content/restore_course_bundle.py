#!/usr/bin/env python

from argparse import ArgumentParser
from getpass import getpass

from nti.deploymenttools.content import configure_logging
from nti.deploymenttools.content import restore_course

import logging
import os
import requests

logger = logging.getLogger('nti_restore_course')
logging.captureWarnings(True)

UA_STRING = 'NextThought Course Restore Utility'

def _parse_args():
    arg_parser = ArgumentParser( description=UA_STRING )
    arg_parser.add_argument( 'coursepath', help="Course archive to restore" )
    arg_parser.add_argument( '-n', '--ntiid', dest='ntiid',
                             help="NTIID of the course to restore." )
    arg_parser.add_argument( '-d', '--dest-server', dest='dest_host',
                             help="Destination server." )
    arg_parser.add_argument( '-u', '--user', dest='user',
                             help="User to authenticate with the server." )
    arg_parser.add_argument( '--site-library', dest='site_library',
                             help="Site library to add content to. Defaults to the hostname of the destination server." )
    arg_parser.add_argument( '-v', '--verbose', dest='loglevel', action='store_const', const=logging.DEBUG,
                             help="Print debugging logs." )
    arg_parser.add_argument( '-q', '--quiet', dest='loglevel', action='store_const', const=logging.WARNING,
                             help="Print warning and error logs only." )
    return arg_parser.parse_args()

def main():
    # Parse command line args
    args = _parse_args()
    course_archive = os.path.abspath(os.path.expanduser(args.coursepath))

    site_library = args.site_library or args.dest_host

    loglevel = args.loglevel or logging.INFO
    configure_logging(level=loglevel)

    try:
        password = getpass('Password for %s@%s: ' % (args.user, args.dest_host))
        logger.info("Restoring course from %s to %s" % (course_archive, args.dest_host))
        course = restore_course( course_archive, args.dest_host, args.user, password, args.ntiid, UA_STRING)
        logger.info('Course restored sucessfully as %s.' % (course['Course']['NTIID'],))

    except requests.exceptions.HTTPError as e:
        logger.error(e)


if __name__ == '__main__': # pragma: no cover
        main()
