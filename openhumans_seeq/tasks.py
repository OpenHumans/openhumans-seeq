from __future__ import absolute_import, print_function

import shutil
import tempfile

from celery import shared_task

from .dataxfer import dataxfer
from .models import OpenHumansMember


@shared_task
def init_xfer_to_open_humans(oh_id, num_submit=0, logger=None, **kwargs):
    """
    Initial transfer of data to Open Humans.

    Because Seeq authorization may take time (for example, the user may need
    to create an account), retry this task a couple times. Each attempt,
    call Seeq to refresh Seeq IDs -- a Seeq ID (1) indicates Seeq authorization
    is complete, and (2) is needed for data retrieval.
    """
    print('Trying to copy data for {} to Open Humans'.format(oh_id))
    OpenHumansMember.update_seeq_ids()
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
    if not oh_member.seeq_id:
        if num_submit < 9:
            num_submit += 1
            init_xfer_to_open_humans.apply_async(
                args=[oh_id, num_submit], kwargs=kwargs,
                countdown=(2 * 2**num_submit))
            print('Resubmitting, num_submit is {}.'.format(num_submit))
            return 'resubmitted'
        else:
            print('Giving up on init xfer for {}.'.format(oh_id))
    else:
        tempdir = tempfile.mkdtemp()
        try:
            dataxfer(oh_member=oh_member, tempdir=tempdir)
        except Exception as inst:
            shutil.rmtree(tempdir)
            raise inst
        shutil.rmtree(tempdir)
