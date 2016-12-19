# Local development instructions

## Local requirements.

1. Foreman https://theforeman.org/manuals/1.13/index.html#3.InstallingForeman
2. RabbitMQ https://www.rabbitmq.com/download.html
3. pip https://pip.pypa.io/en/stable/installing/

## Install Python requirements.

**Strongly recommend you use [virtualenv](https://virtualenv.pypa.io/en/stable/).**

`pip install -r requirements.txt`

## Set up `.env`

Copy `env.example` to `.env`.

This file contains secrets and other configurations for running the app.
When you use foreman to run this app, it will load `.env` to be environment
variables.<br>**Keep your version SECRET! Never commit it to git.</b>**

## Create Open Humans & Seeq projects

You need to create new projects for development purposes. For example, you
can't re-use the production Open Humans app because you'll need to set your
app's redirect_uri to point to localhost.

## Initalize database.

Note: Django will use SQLite3 for local development unless you set
`DATABASE_URL` in your `.env`.

### Initialize database.

In the project directory, run the `migrate` command with foreman:
`foreman run python manage.py migrate`

## Run.

`foreman start`

Go to http://127.0.0.1:5000/
