from __future__ import print_function

import hashlib
import json
import os
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import requests
import seeq

from .utils import oh_get_member_data

OH_API_BASE = 'https://www.openhumans.org/api/direct-sharing'
MAX_FILESIZE = 1000000000  # Max of 1GB file to Open Humans.
SEEQ_REFRESH_TOKEN = os.getenv('SEEQ_REFRESH_TOKEN')
SEEQ_STUDY_ID = int(os.getenv('SEEQ_STUDY_ID'))


def get_md5(filepath):
    file_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            file_md5.update(chunk)
    return file_md5.hexdigest()


def oh_upload_to_s3(oh_member, filepath, filename=None,
                    tags=[], description=''):
    """
    Upload a file to Open Humans S3 via three-step process.

    Give Open Humans metadata and get an S3 upload URL from Open Humans.
    Upload the file to this URL. Then notify Open Humans upload is done.
    """
    upload_url = '{}/project/files/upload/direct/?access_token={}'.format(
        OH_API_BASE, oh_member.get_access_token())
    if not filename:
        filename = os.path.basename(filepath)
    metadata = {
        'tags': tags,
        'description': description,
        'md5': get_md5(filepath),
    }
    req1 = requests.post(
        upload_url,
        data={'project_member_id': oh_member.oh_id,
              'filename': filename,
              'metadata': json.dumps(metadata)})
    if req1.status_code != 201:
        print('Bad response in starting upload: {}'.format(req1.status_code))
        return
    with open(filepath, 'rb') as fh:
        req2 = requests.put(url=req1.json()['url'], data=fh)
    if req2.status_code != 200:
        print('Bad response in upload to S3: {}'.format(req2.status_code))
        return
    complete_url = (
        '{}/project/files/upload/complete/?'
        'access_token={}'.format(OH_API_BASE, oh_member.get_access_token()))
    req3 = requests.post(
        complete_url,
        data={'project_member_id': oh_member.oh_id,
              'file_id': req1.json()['id']})
    if req3.status_code != 200:
        print('Bad response in completing upload: {}'.format(req3.status_code))
    else:
        print('Upload complete for "{}".'.format(filename))


def seeq_file_to_oh(oh_member, seeq_data, tempdir):
    """
    Copy a Seeq file to Open Humans.

    Somewhat inefficient: downloads a file from one S3 bucket and uploads to
    another.
    """
    seeq_filename = urlparse.urlsplit(seeq_data['url_s3'])[2].split('/')[-1]
    target_filepath = os.path.join(tempdir, seeq_filename)
    response = requests.get(seeq_data['url_s3'], stream=True)
    size = int(response.headers['Content-Length'])
    if size > MAX_FILESIZE:
        print("Skipping: Seeq file {} is larger than {} bytes".format(
            seeq_filename, MAX_FILESIZE))
        return
    print("Downloading {}...".format(seeq_filename))
    with open(target_filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print("Uploading {}...".format(seeq_filename))
    oh_upload_to_s3(oh_member=oh_member,
                    filepath=target_filepath,
                    filename=seeq_filename,
                    tags=[],
                    description=('Seeq project raw data. Contains personal '
                                 'genetic and microbiome information.'))


def dataxfer(oh_member, tempdir):
    """
    Copy Seeq files into Open Humans if not already present.

    Seeq filenames are used as Open Humans filenames. Check if a file with this
    filename is already in Open Humans. If not, download from Seeq and upload
    to Open Humans.
    """
    c = seeq.client.Client(None)
    c.set_refresh_token(SEEQ_REFRESH_TOKEN)
    oh_data = oh_get_member_data(oh_member.get_access_token())
    oh_filenames = [f['basename'] for f in oh_data['data']]
    seeq_data = c.study_raw_data_get(SEEQ_STUDY_ID, [oh_member.seeq_id])
    for item in seeq_data:
        seeq_filename = urlparse.urlsplit(item['url_s3'])[2].split('/')[-1]
        if seeq_filename not in oh_filenames:
            print('Copying {} to Open Humans...'.format(seeq_filename))
            seeq_file_to_oh(oh_member, item, tempdir)
        else:
            print('File "{}" already in Open Humans.'.format(seeq_filename))
