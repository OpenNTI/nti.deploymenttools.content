from zipfile import ZipFile
from zope.exceptions.log import Formatter as ZopeLogFormatter

import logging
import os
import requests
import simplejson as json

logger = logging.getLogger(__name__)

def archive_directory( path, archive_path ):
    base_path = path + os.sep
    logger.debug(base_path)

    with ZipFile(archive_path, 'w') as archive:
        logger.debug('Creating archive %s' % (archive_path,))
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root,file)
                archive_file_path = file_path.replace(base_path,'')
                logger.debug('Adding %s to the archive as %s.' % (file_path, archive_file_path))
                archive.write(file_path, archive_file_path)


DEFAULT_LOG_FORMAT = '[%(asctime)-15s] [%(name)s] %(levelname)s: %(message)s'

def configure_logging(level=logging.INFO, fmt=DEFAULT_LOG_FORMAT):
    level = logging.INFO if not isinstance(level, int) else level
    logging.basicConfig(level=level)
    logging.root.handlers[0].setFormatter(ZopeLogFormatter(fmt))


CHUNK_SIZE=1024*1024

def download_rendered_content( content_ntiid, host, username, password, ua_string ):
    url = 'https://%s/dataserver2/Objects/%s/@@Export' % (host, content_ntiid)
    headers = {
        'user-agent': ua_string
    }

    content_archive = '.'.join( [ content_ntiid, 'zip'] )
    response = requests.get(url, stream=True, headers=headers, auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests.codes.ok:
        with open(content_archive, 'wb') as archive:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    archive.write(chunk)
        return content_archive


def export_course( course_ntiid, host, username, password, ua_string, backup=False ):
    url = 'https://%s/dataserver2/Objects/%s/@@Export' % (host, course_ntiid)
    headers = {
        'user-agent': ua_string,
        'Content-Type': 'application/json'
    }

    body = {
        'backup': backup
    }

    course_archive = '.'.join( [ course_ntiid, 'zip'] )
    response = requests.get(url, stream=True, headers=headers, data=json.dumps(body), auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests.codes.ok:
        with open(course_archive, 'wb') as archive:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    archive.write(chunk)
        return course_archive

def import_course( course, host, username, password, site_library, admin_level, provider_id, ua_string ):
    url = 'https://%s/dataserver2/CourseAdmin/@@ImportCourse' % host
    headers = {
        'user-agent': ua_string
    }

    files = {'data': open(course, 'rb')}

    data = { 
        'admin': admin_level,
        'key': provider_id,
        'site': site_library 
    }

    response = requests.post(url, headers=headers, files=files, data=data, auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests.codes.ok:
        return response.json()


def upload_rendered_content( content, host, username, password, site_library, ua_string ):
    url = 'https://%s/dataserver2/Library/@@ImportRenderedContent' % host
    headers = {
        'user-agent': ua_string
    }

    files = {'data': open(content, 'rb')}

    data = { 'site': site_library }

    response = requests.post(url, headers=headers, files=files, data=data, auth=(username, password))
    response.raise_for_status()
    if response.status_code == requests.codes.ok:
        return response.json()
