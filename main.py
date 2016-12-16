import os

from flask import Flask, render_template, request
import requests

CLIENT_ID = os.getenv('OH_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('OH_CLIENT_SECRET', '')
OH_BASE_URL = 'https://www.openhumans.org/'
OHSEEQ_BASE_URL = os.getenv('DATAXFER_BASE_URL', 'http://127.0.0.1:5000/')
OH_PROJ_PAGE = 'https://www.openhumans.org/activity/seeq/'

# Default to DEBUG as True.
DEBUG = False if os.getenv('DEBUG', '').lower() == 'False' else True

app = Flask(__name__)

# Set up Flask app to log to stderr.
import logging
from logging import StreamHandler
file_handler = StreamHandler()
if DEBUG:
    app.logger.setLevel(logging.DEBUG)
else:
    app.logger.setLevel(logging.INFO)
app.logger.addHandler(file_handler)


def exchange_code(code):
    if CLIENT_SECRET and CLIENT_ID and code:
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': '{}complete'.format(OHSEEQ_BASE_URL),
            'code': code,
        }
        req = requests.post(
            '{}oauth2/token/'.format(OH_BASE_URL),
            data=data,
            auth=requests.auth.HTTPBasicAuth(
                CLIENT_ID,
                CLIENT_SECRET
            ))
        if 'access_token' in req.json():
            return req.json()['access_token']
        elif 'error' in req.json():
            app.logger.warning('Error in token exchange: {}'.format(req.json()))
        else:
            app.logger.warning('Neither token nor error info in OH response!')
    else:
        app.logger.warning('CLIENT_SECRET or code are unavailable')
    return ''


@app.route("/")
def index():
    app.logger.debug("Loading index.html")
    return render_template(
        'index.html', client_id=CLIENT_ID, oh_proj_page=OH_PROJ_PAGE)


@app.route("/complete", methods=['GET'])
def complete():
    app.logger.debug("Loading complete.html")
    code = request.args.get('code', '')
    token = exchange_code(code=code)
    return render_template('complete.html', code=code, token=token)
