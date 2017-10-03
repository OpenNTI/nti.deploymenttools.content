from zipfile import ZipFile

import logging
import os
import requests

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
        logger.info('Render sucessfully uploaded.')

