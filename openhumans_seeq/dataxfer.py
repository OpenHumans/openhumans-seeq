from __future__ import print_function

import os

import seeq

SEEQ_REFRESH_TOKEN = os.getenv('SEEQ_REFRESH_TOKEN')
SEEQ_STUDY_ID = int(os.getenv('SEEQ_STUDY_ID'))


def dataxfer(oh_member, tempdir=None):
    """
    Placeholder for individual Seeq data transfer to Open Humans.
    """
    c = seeq.client.Client(None)
    c.set_refresh_token(SEEQ_REFRESH_TOKEN)
    raw_data = c.study_raw_data_get(SEEQ_STUDY_ID, [oh_member.seeq_id])
    print('Placeholder for dataxfer for {}: {}'.format(
        oh_member.oh_id, raw_data))
