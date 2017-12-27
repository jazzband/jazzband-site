import sys

import click
from flask.cli import with_appcontext

from .models import db, redis
from .members.commands import sync_members, sync_user_email_addresses
from .projects.commands import sync_projects, send_new_upload_notifications


@click.command('db')
@with_appcontext
def check_db():
    "Checks database connection"
    try:
        db.session.execute('SELECT 1;')
    except Exception as exc:
        print(f'Database connection failed: {exc}')
        sys.exit(1)


@click.command('redis')
@with_appcontext
def check_redis():
    "Checks database connection"
    try:
        response = redis.ping()
    except Exception:
        response = None
    if not response:
        print('Redis ping failed.')
        sys.exit(1)


def init_app(app):

    @app.cli.group()
    def check():
        "Checks some backends."

    @app.cli.group()
    def send():
        "Send notifications."

    @app.cli.group()
    def sync():
        "Sync Jazzband data."

    check.add_command(check_db)
    check.add_command(check_redis)

    send.add_command(send_new_upload_notifications)

    sync.add_command(sync_members)
    sync.add_command(sync_user_email_addresses)
    sync.add_command(sync_projects)
