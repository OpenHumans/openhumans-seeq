from datetime import timedelta
import os
import shutil
import tempfile
import time

import arrow
from celery import Celery
from celery.signals import task_postrun
from flask import Flask, redirect, render_template, request
from flask_sqlalchemy import SQLAlchemy
import requests
import seeq

from dataxfer import dataxfer

# Celery settings
CELERY_BROKER_URL = os.getenv('CLOUDAMQP_URL', 'amqp://')

# Open Humans settings
OH_CLIENT_ID = os.getenv('OH_CLIENT_ID', '')
OH_CLIENT_SECRET = os.getenv('OH_CLIENT_SECRET', '')
OH_BASE_URL = 'https://www.openhumans.org/'

# SEEQ settings
SEEQ_REFRESH_TOKEN = os.getenv('SEEQ_REFRESH_TOKEN')
SEEQ_API_KEY_PRODUCTION = os.getenv('SEEQ_API_KEY_PRODUCTION')
SEEQ_STUDY_ID = int(os.getenv('SEEQ_STUDY_ID'))

# Project details
OHSEEQ_BASE_URL = os.getenv('OHSEEQ_BASE_URL', 'http://127.0.0.1:5000/')
OH_PROJ_PAGE = 'https://www.openhumans.org/activity/seeq/'

# Default to DEBUG as True.
DEBUG = False if os.getenv('DEBUG', '').lower() == 'False' else True

# Set up Flask app.
app = Flask(__name__)
app.config.update(
    DEBUG=DEBUG,
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False)

# Set up database.
db = SQLAlchemy(app)


class OpenHumansMember(db.Model):
    """
    Store OAuth2 data for Open Humans member.
    """
    oh_id = db.Column(db.String, primary_key=True, unique=True)
    access_token = db.Column(db.String)
    refresh_token = db.Column(db.String)
    token_expires = db.Column(db.String)
    seeq_id = db.Column(db.Integer, nullable=True)

    def __init__(self, oh_id, access_token, refresh_token, expires_in):
        self.oh_id = oh_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires = (
            arrow.now() + timedelta(seconds=expires_in)).format()

    def __repr__(self):
        return "<OpenHumansMember(oh_id='{}', seeq_id='{}')>".format(
            self.oh_id, self.seeq_id)

    def get_access_token(self):
        """
        Return access token. Refresh first if necessary.
        """
        # Also refresh if nearly expired (less than 60s remaining).
        delta = timedelta(seconds=60)
        if arrow.get(self.token_expires) - delta < arrow.now():
            self._refresh_tokens()
        return self.access_token

    def _refresh_tokens(self):
        """
        Refresh access token.
        """
        response = requests.post(
            'https://www.openhumans.org/oauth2/token/',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token},
            auth=requests.auth.HTTPBasicAuth(
                OH_CLIENT_ID, OH_CLIENT_SECRET))
        if response.status_code == 200:
            data = response.json()
            self.access_token = data['access_token']
            self.refresh_token = data['refresh_token']
            self.token_expires = (
                arrow.now() + timedelta(seconds=data['expires_in'])).format()
            db.session.commit()

    @classmethod
    def update_seeq_ids(cls):
        """
        Run to update all users in our database with Seeq IDs where available.
        """
        c = seeq.client.Client(None)
        c.set_refresh_token(SEEQ_REFRESH_TOKEN)
        participants = c.study_participants_get(SEEQ_STUDY_ID)
        for user in participants:
            oh_member = cls.query.filter_by(
                oh_id=user['external_id']).one_or_none()
            if not oh_member:
                app.logger.warning('Seeq reports external_id "{}" with no '
                                   'match in db!'.format(user['external_id']))
                continue
            if not oh_member.seeq_id:
                oh_member.seeq_id = user['id']
                db.session.commit()


# Set up Celery with Heroku CloudAMQP (or AMQP in local dev).
celery = Celery(__name__)
celery.conf.update({
    'BROKER_URL': CELERY_BROKER_URL,
    # Recommended settings. See: https://www.cloudamqp.com/docs/celery.html
    'BROKER_POOL_LIMIT': 1,
    'BROKER_HEARTBEAT': None,
    'BROKER_CONNECTION_TIMEOUT': 30,
    'CELERY_RESULT_BACKEND': None,
    'CELERY_SEND_EVENTS': False,
    'CELERY_EVENT_QUEUE_EXPIRES': 60,
})


@task_postrun.connect
def post_task_cleanup(*args, **kwargs):
    """
    Clean up temporary files.

    By running this as a postrun signal, clean-up occurs regardless of errors
    or bugs in running the task.
    """
    if 'retval' != 'resubmitted' and 'tempdir' in kwargs['kwargs']:
        try:
            shutil.rmtree(kwargs['kwargs']['tempdir'])
        except OSError:
            pass


@celery.task
def init_xfer_to_open_humans(oh_id, tempdir, num_submit=0, **kwargs):
    """
    Initial transfer of data to Open Humans.

    Because Seeq authorization may take time (for example, the user may need
    to create an account), retry this task a couple times. Each attempt,
    call Seeq to refresh Seeq IDs -- a Seeq ID (1) indicates Seeq authorization
    is complete, and (2) is needed for data retrieval.
    """
    app.logger.info('Trying to copy data for {} to Open Humans'.format(oh_id))
    OpenHumansMember.update_seeq_ids()
    oh_member = OpenHumansMember.query.filter_by(oh_id=oh_id).one()
    if not oh_member.seeq_id:
        if num_submit < 9:
            num_submit += 1
            init_xfer_to_open_humans.apply_async(
                args=[oh_id, tempdir, num_submit], kwargs=kwargs,
                countdown=(2 * 2**num_submit))
            return 'resubmitted'
        else:
            app.logger.info('Giving up on init xfer for {}.'.format(oh_id))
    else:
        dataxfer(oh_member=oh_member, tempdir=tempdir, logger=app.logger)


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
            oh_member = OpenHumansMember.query.filter_by(
                oh_id=oh_id).one_or_none()
            if not oh_member:
                oh_member = OpenHumansMember(
                    oh_id=oh_id,
                    access_token=data['access_token'],
                    refresh_token=data['refresh_token'],
                    expires_in=data['expires_in'])
                db.session.add(oh_member)
                app.logger.info('Member {} added.'.format(oh_id))
            else:
                app.logger.info('Member {} re-authorized.'.format(oh_id))
                oh_member.access_token = data['access_token']
                oh_member.refresh_token = data['refresh_token']
                oh_member.token_expires = (arrow.now() + timedelta(
                    seconds=data['expires_in'])).format()
            db.session.commit()
            return oh_member
        elif 'error' in req.json():
            app.logger.warning('Error in token exchange: {}'.format(req.json()))
        else:
            app.logger.warning('Neither token nor error info in OH response!')
    else:
        app.logger.warning('OH_CLIENT_SECRET or code are unavailable')
    return None


@app.route("/")
def index():
    """
    Starting page for app.
    """
    return render_template(
        'index.html', client_id=OH_CLIENT_ID, oh_proj_page=OH_PROJ_PAGE)


@app.route("/complete", methods=['GET'])
def complete():
    """
    Receive user from Open Humans. Store data, start task, prompt Seeq auth.
    """
    app.logger.debug("Received user returning from Open Humans.")
    code = request.args.get('code', '')
    oh_member = oh_code_to_member(code=code)
    if oh_member:
        tempdir = tempfile.mkdtemp()
        init_xfer_to_open_humans.delay(oh_id=oh_member.oh_id, tempdir=tempdir)
        seeq_url = seeq.util.jwt_signed(
            SEEQ_STUDY_ID,
            oh_member.oh_id,
            SEEQ_API_KEY_PRODUCTION)
        return render_template(
            'complete.html', oh_id=oh_member.oh_id, seeq_url=seeq_url)
    app.logger.info('Invalid code exchange. User returned to starting page.')
    return redirect('/')
