"""
Celery set up, as recommended by celery
http://celery.readthedocs.org/en/latest/django/first-steps-with-django.html
"""
# absolute_import prevents conflicts between project celery.py file
# and the celery package.
from __future__ import absolute_import

import os
import shutil

from celery import Celery
from celery.signals import task_postrun

from django.conf import settings

CELERY_BROKER_URL = os.getenv('CLOUDAMQP_URL', 'amqp://')

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'openhumans_seeq.settings')

app = Celery('genevieve_client', broker=CELERY_BROKER_URL)
# Set up Celery with Heroku CloudAMQP (or AMQP in local dev).
app.conf.update({
    'BROKER_URL': CELERY_BROKER_URL,
    # Recommended settings. See: https://www.cloudamqp.com/docs/celery.html
    'BROKER_POOL_LIMIT': 1,
    'BROKER_HEARTBEAT': None,
    'BROKER_CONNECTION_TIMEOUT': 30,
    'CELERY_RESULT_BACKEND': None,
    'CELERY_SEND_EVENTS': False,
    'CELERY_EVENT_QUEUE_EXPIRES': 60,
})


# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


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
