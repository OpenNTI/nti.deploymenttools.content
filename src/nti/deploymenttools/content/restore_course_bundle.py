#!/usr/bin/env python

from argparse import ArgumentParser
from getpass import getpass

from nti.deploymenttools.content import configure_logging
from nti.deploymenttools.content import restore_course
from nti.deploymenttools.content.copy_course import _get_content_packages

import logging
import os
import requests

logger = logging.getLogger('nti_restore_course')
logging.captureWarnings(True)

UA_STRING = 'NextThought Course Restore Utility'

def _restore_course(course_archive, dest_host, username):
    try:
        password = getpass('Password for %s@%s: ' % (username, dest_host))
        logger.info("Restoring course from %s to %s" % (course_archive, dest_host))
        course = restore_course( course_archive, dest_host, username, password, UA_STRING)
        logger.info('Course restored sucessfully as %s.' % (course['Course']['NTIID'],))

    except requests.exceptions.HTTPError as e:
        logger.error(e)

def _parse_args():
    arg_parser = ArgumentParser( description=UA_STRING )
    arg_parser.add_argument( 'coursepath', help="Course archive to restore" )
    arg_parser.add_argument( '-d', '--dest-server', dest='dest_host',
                             help="Destination server." )
    arg_parser.add_argument( '-u', '--user', dest='user',
                             help="User to authenticate with the server." )
    arg_parser.add_argument( '-a', '--admin-level', dest='admin_level', default='DefaultAPIRestored',
                             help="Specifies the organizational admin level for the course." )
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

    _restore_course( course_archive,
                 args.dest_host,
                 args.user)

if __name__ == '__main__': # pragma: no cover
        main()
