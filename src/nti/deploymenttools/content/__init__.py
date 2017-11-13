#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import shutil
import logging
import tempfile
from zipfile import ZipFile

import requests

from zope.exceptions.log import Formatter as ZopeLogFormatter

logger = __import__('logging').getLogger(__name__)

requests_codes = requests.codes


def archive_directory(source_path, archive_path):
    if not os.path.isdir(source_path):
        raise ValueError("Invalid source path")
    logger.debug("Archiving %s", source_path)
    filename = tempfile.mktemp()
    try:
        shutil.make_archive(filename, "zip", source_path, source_path)
    finally:
        logger.debug('Creating archive %s' % (archive_path,))
        shutil.move(filename + ".zip", archive_path)
    return archive_path


DEFAULT_LOG_FORMAT = '[%(asctime)-15s] [%(name)s] %(levelname)s: %(message)s'


def configure_logging(level=logging.INFO, fmt=DEFAULT_LOG_FORMAT):
    level = logging.INFO if not isinstance(level, int) else level
    logging.basicConfig(level=level)
    logging.root.handlers[0].setFormatter(ZopeLogFormatter(fmt))


CHUNK_SIZE = 1024 * 1024


def download_rendered_content(content_ntiid, host, username, password, ua_string):
    url = 'https://%s/dataserver2/Objects/%s/@@Export' % (host, content_ntiid)
    headers = {
        'user-agent': ua_string
    }
    content_archive = '.'.join([content_ntiid, 'zip'])
    response = requests.get(url, stream=True, headers=headers,
                            auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests_codes.ok:
        with open(content_archive, 'wb') as archive:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    archive.write(chunk)
        return content_archive


def export_course(course_ntiid, host, username, password, ua_string, backup=False):
    url = 'https://%s/dataserver2/Objects/%s/@@Export' % (host, course_ntiid)
    headers = {
        'user-agent': ua_string
    }
    body = {
        'backup': backup
    }
    course_archive = '.'.join([course_ntiid, 'zip'])
    response = requests.get(url, stream=True, headers=headers,
                            params=body, auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests_codes.ok:
        with open(course_archive, 'wb') as archive:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    archive.write(chunk)
        return course_archive


def import_course(course, host, username, password, site_library, 
                  admin_level, provider_id, ua_string):
    url = 'https://%s/dataserver2/CourseAdmin/@@ImportCourse' % host
    headers = {
        'user-agent': ua_string
    }
    with open(course, "rb") as fp:
        files = {'data': fp}
        data = {
            'admin': admin_level,
            'key': provider_id,
            'writeout': "True",
            'site': site_library,
        }
        response = requests.post(url, headers=headers,
                                 files=files, data=data, 
                                 auth=(username, password))
        response.raise_for_status()
        if response.status_code == requests_codes.ok:
            return response.json()


def restore_course(course, host, username, password, ntiid, ua_string):
    url = 'https://%s/dataserver2/Objects/%s/@@Import' % (host, ntiid)
    headers = {
        'user-agent': ua_string
    }
    with open(course, "rb") as fp:
        files = {'data': fp}
        response = requests.post(url, headers=headers, files=files, 
                                 auth=(username, password))
        response.raise_for_status()
        if response.status_code == requests_codes.ok:
            return response.json()


def upload_rendered_content(content, host, username, password, 
                            site_library, ua_string):
    url = 'https://%s/dataserver2/Library/@@ImportRenderedContent' % host
    headers = {
        'user-agent': ua_string
    }
    with open(content, "rb") as fp:
        files = {'data': fp}
        data = {
            'obfuscate': True,
            'site': site_library
        }
        response = requests.post(url, headers=headers,
                                 files=files, data=data, 
                                 auth=(username, password))
        response.raise_for_status()
        if response.status_code == requests_codes.ok:
            return response.json()
