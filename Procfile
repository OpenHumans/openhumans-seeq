web: gunicorn openhumans_seeq.wsgi --log-file -
worker: celery -A openhumans_seeq worker --without-gossip --without-mingle --without-heartbeat
