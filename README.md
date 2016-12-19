# Local development instructions

## Local requirements.

1. Foreman https://theforeman.org/manuals/1.13/index.html#3.InstallingForeman
2. PostgreSQL https://wiki.postgresql.org/wiki/Detailed_installation_guides
3. RabbitMQ https://www.rabbitmq.com/download.html
4. pip https://pip.pypa.io/en/stable/installing/

## Install Python requirements.

**Strongly recommend you use [virtualenv](https://virtualenv.pypa.io/en/stable/).**

`pip install -r requirements.txt`

## Set up `.env`

Copy `env.example` to `.env`.

Use this file to store secrets and other configurations for running the app.<br>
**Keep your version SECRET! Never commit it to git.</b>**

## Create Open Humans & Seeq projects

You need to create new projects for development purposes. For example, you can't re-use the production Open Humans app because you'll need to set your app's redirect_uri to point to localhost.

## Set up PostgreSQL and initalize database.

### Install PostgreSQL.

Create a database and set DATABASE_URL appropriately. For example, do the following in Ubuntu:
1. `sudo su - postgres`
2. `createdb ohseeq`
3. `createuser -P ohseeq`
4. Enter 'ohseeq' as password.
5. `psql ohseeq`
6. (in psql) `GRANT ALL PRIVILEGES ON DATABASE ohseeq TO ohseeq;`
7. (in psql) `\q`
8. `exit`
9. Set DATABASE_URL in .env: `DATABASE_URL="postgres://ohseeq:ohseeq@127.0.0.1/ohseeq"`

### Initialize database.

In the project directory, start python using foreman: `foreman run python`

Then, in python, run the following:
```
from main import db
db.create_all()
```

## Run.

`foreman start`

Go to http://127.0.0.1:5000/
