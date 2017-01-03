from __future__ import print_function

import os
import shutil
import tempfile

from django.core.management.base import BaseCommand

from openhumans_seeq.dataxfer import dataxfer
from openhumans_seeq.models import OpenHumansMember

SEEQ_REFRESH_TOKEN = os.getenv('SEEQ_REFRESH_TOKEN')
SEEQ_STUDY_ID = int(os.getenv('SEEQ_STUDY_ID'))


class Command(BaseCommand):
    help = 'Sync all current Seeq data for Open Humans members.'

    def _sync_all(self, tempdir):
        print('Syncing member data using tempdir "{}"...'.format(tempdir))
        OpenHumansMember.update_seeq_ids()
        for oh_member in OpenHumansMember.objects.all():
            print('Syncing member {}...'.format(oh_member.oh_id))
            if not oh_member.seeq_id:
                print('Member {} has no corresponding Seeq ID.')
                continue
            dataxfer(oh_member, tempdir=tempdir)

    def handle(self, *args, **options):
        tempdir = tempfile.mkdtemp()
        try:
            self._sync_all(tempdir)
        except Exception as inst:
            shutil.rmtree(tempdir)
            raise inst
        shutil.rmtree(tempdir)
