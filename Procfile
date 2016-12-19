web: gunicorn main:app --log-file=-
worker: celery -A main.celery worker --without-gossip --without-mingle --without-heartbeat
