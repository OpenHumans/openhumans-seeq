"""
WSGI config for openhumans_seeq project.
"""

import os

from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openhumans_seeq.settings")

application = get_wsgi_application()
application = DjangoWhiteNoise(application)
