import logging
import os
import tempfile

from django.shortcuts import redirect, render
import requests
import seeq

from .models import OpenHumansMember
from .tasks import init_xfer_to_open_humans

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Open Humans settings
OH_CLIENT_ID = os.getenv('OH_CLIENT_ID', '')
OH_CLIENT_SECRET = os.getenv('OH_CLIENT_SECRET', '')
OH_BASE_URL = 'https://www.openhumans.org/'

# SEEQ settings
SEEQ_API_KEY_PRODUCTION = os.getenv('SEEQ_API_KEY_PRODUCTION')
SEEQ_STUDY_ID = int(os.getenv('SEEQ_STUDY_ID'))

# Project details
OHSEEQ_BASE_URL = os.getenv('OHSEEQ_BASE_URL', 'http://127.0.0.1:5000/')
OH_PROJ_PAGE = 'https://www.openhumans.org/activity/seeq/'


def oh_get_member_data(token):
    """
    Exchange OAuth2 token for member data.
    """
    req = requests.get(
        '{}api/direct-sharing/project/exchange-member/'.format(OH_BASE_URL),
        params={'access_token': token})
    if req.status_code == 200:
        return req.json()
    raise Exception('Status code {}'.format(req.status_code))
    return None


def oh_code_to_member(code):
    """
    Exchange code for token, use this to create and return OpenHumansMember.

    If a matching OpenHumansMember already exists in db, update and return it.
    """
    if OH_CLIENT_SECRET and OH_CLIENT_ID and code:
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': '{}complete'.format(OHSEEQ_BASE_URL),
            'code': code,
        }
        req = requests.post(
            '{}oauth2/token/'.format(OH_BASE_URL),
            data=data,
            auth=requests.auth.HTTPBasicAuth(
                OH_CLIENT_ID,
                OH_CLIENT_SECRET
            ))
        data = req.json()
        if 'access_token' in data:
            oh_id = oh_get_member_data(
                data['access_token'])['project_member_id']
            try:
                oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
                logger.info('Member {} re-authorized.'.format(oh_id))
                oh_member.access_token = data['access_token']
                oh_member.refresh_token = data['refresh_token']
                oh_member.token_expires = OpenHumansMember.get_expiration(
                    data['expires_in'])
            except OpenHumansMember.DoesNotExist:
                oh_member = OpenHumansMember.create(
                    oh_id=oh_id,
                    access_token=data['access_token'],
                    refresh_token=data['refresh_token'],
                    expires_in=data['expires_in'])
                logger.info('Member {} created.'.format(oh_id))
            oh_member.save()
            return oh_member
        elif 'error' in req.json():
            logger.warning('Error in token exchange: {}'.format(req.json()))
        else:
            logger.warning('Neither token nor error info in OH response!')
    else:
        logger.warning('OH_CLIENT_SECRET or code are unavailable')
    return None


def index(request):
    """
    Starting page for app.
    """
    context = {'client_id': OH_CLIENT_ID, 'oh_proj_page': OH_PROJ_PAGE}
    return render(request, 'openhumans_seeq/index.html', context=context)


def complete(request):
    """
    Receive user from Open Humans. Store data, start task, prompt Seeq auth.
    """
    logger.debug("Received user returning from Open Humans.")
    code = request.GET.get('code', '')
    oh_member = oh_code_to_member(code=code)
    if oh_member:
        tempdir = tempfile.mkdtemp()
        init_xfer_to_open_humans.delay(oh_id=oh_member.oh_id, tempdir=tempdir)
        seeq_url = seeq.util.jwt_signed(
            SEEQ_STUDY_ID,
            oh_member.oh_id,
            SEEQ_API_KEY_PRODUCTION)
        context = {'oh_id': oh_member.oh_id, 'seeq_url': seeq_url}
        return render(request, 'openhumans_seeq/complete.html',
                      context=context)
    logger.info('Invalid code exchange. User returned to starting page.')
    return redirect('/')
