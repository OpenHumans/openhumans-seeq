from datetime import timedelta
import os

import arrow
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
import requests
import seeq

OH_CLIENT_ID = os.getenv('OH_CLIENT_ID', '')
OH_CLIENT_SECRET = os.getenv('OH_CLIENT_SECRET', '')

SEEQ_REFRESH_TOKEN = os.getenv('SEEQ_REFRESH_TOKEN')
SEEQ_STUDY_ID = int(os.getenv('SEEQ_STUDY_ID'))


@python_2_unicode_compatible
class OpenHumansMember(models.Model):
    """
    Store OAuth2 data for Open Humans member.
    """
    oh_id = models.CharField(max_length=16, primary_key=True, unique=True)
    access_token = models.CharField(max_length=256)
    refresh_token = models.CharField(max_length=256)
    token_expires = models.DateTimeField()
    seeq_id = models.IntegerField(null=True)

    @staticmethod
    def get_expiration(expires_in):
        return (arrow.now() + timedelta(seconds=expires_in)).format()

    @classmethod
    def create(cls, oh_id, access_token, refresh_token, expires_in):
        oh_member = cls(
            oh_id=oh_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires=cls.get_expiration(expires_in))
        return oh_member

    def __str__(self):
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
            self.token_expires = self.get_expiration(data['expires_in'])
            self.save()

    @classmethod
    def update_seeq_ids(cls):
        """
        Run to update all users in our database with Seeq IDs where available.
        """
        c = seeq.client.Client(None)
        c.set_refresh_token(SEEQ_REFRESH_TOKEN)
        participants = c.study_participants_get(SEEQ_STUDY_ID)
        for user in participants:
            try:
                oh_member = cls.objects.get(oh_id=user['external_id'])
            except cls.DoesNotExist:
                print('Seeq reports external_id "{}" with no '
                      'match in db!'.format(user['external_id']))
                continue
            if not oh_member.seeq_id:
                oh_member.seeq_id = user['id']
                oh_member.save()
