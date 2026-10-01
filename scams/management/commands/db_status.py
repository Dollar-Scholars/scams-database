"""
python manage.py db_status

Shows which database Django is configured for, whether it can connect, the
server version, whether the connection is encrypted (PostgreSQL), which
migrations are still pending, and how many scam reports are stored.
The database password is never printed.
"""

import re
import sqlite3
import time
from pathlib import Path

import django
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, NotSupportedError, connections
from django.db.migrations.loader import MigrationLoader

LOCAL_HOSTS = ('', 'localhost', '127.0.0.1', '::1')

# Django connects, then refuses a server older than it supports, e.g. Django 5.2:
# "PostgreSQL 14 or later is required (found 13.16)."
UNSUPPORTED_VERSION = re.compile(r'(?P<minimum>\d+(?:\.\d+)*) or later is required \(found ')

# (any of these substrings in the driver's error message, hint to show).
# Ordered from most to least specific: the first match wins.
FAILURE_HINTS = [
    (
        # Before the ssl hint: the message repeats the host name, which may contain "ssl".
        ('failed to resolve host', 'getaddrinfo', 'could not translate host name',
         'name or service not known', 'nodename nor servname', 'unknown host'),
        'POSTGRES_HOST could not be resolved. Use the VM\'s IP address or a name this computer can resolve.',
    ),
    (
        ('connection refused',),
        'Nothing is accepting connections on that host/port. On the VM check the '
        'service is running (pg_lsclusters, or sudo systemctl status postgresql@<version>-main; '
        'logs: sudo journalctl -u postgresql@<version>-main), that postgresql.conf has '
        "listen_addresses = '*' (or the VM's IP) and the right port, then restart PostgreSQL.",
    ),
    (
        ('timeout expired', 'timed out'),
        'No answer in time: usually a firewall, a wrong IP, or (on Windows, where a refused '
        'connection can also look like a timeout) nothing listening on that port. Check '
        'POSTGRES_HOST/POSTGRES_PORT, that the VM and PostgreSQL are up, listen_addresses, and '
        'that TCP port {port} is open on the VM (e.g. sudo ufw allow from <this-computer-ip> '
        'to any port {port} proto tcp) and in any hypervisor/cloud firewall.',
    ),
    (
        ('no pg_hba.conf entry',),
        'The server is reachable but refuses this client. Add a line for this computer to '
        'pg_hba.conf, e.g. "hostssl  <db>  <user>  <this-computer-ip>/32  scram-sha-256", '
        'then run: sudo systemctl reload postgresql',
    ),
    (
        ('password authentication failed', 'no password supplied'),
        'Wrong POSTGRES_USER or POSTGRES_PASSWORD (check .env for typos and stray quotes), '
        "or the role has no password yet: ALTER ROLE <user> WITH LOGIN PASSWORD '...';",
    ),
    (
        ('ssl', 'certificate'),
        'SSL negotiation failed. "server does not support SSL" means ssl = on is not set in '
        'postgresql.conf (enable it, or use POSTGRES_SSLMODE=prefer/disable on a trusted '
        'network). verify-ca/verify-full also need the server CA certificate on this computer.',
    ),
    (
        ('does not exist',),
        'Connected, but the database or role does not exist on the server. Create it '
        '(CREATE ROLE ... / CREATE DATABASE ... OWNER ...) or fix POSTGRES_DB / POSTGRES_USER.',
    ),
]

CHECKLIST = [
    "postgresql.conf: listen_addresses = '*' (or the VM's IP); restart after changing it",
    'pg_hba.conf: a hostssl (or host) line for this computer\'s IP with scram-sha-256; reload after changing it',
    'Firewall on the VM (and hypervisor/cloud) allows TCP {port} from this computer',
    'POSTGRES_SSLMODE matches the server (require needs ssl = on in postgresql.conf)',
    'POSTGRES_USER / POSTGRES_PASSWORD are correct',
    'Full guide: docs/POSTGRES.md (Troubleshooting)',
]


class Command(BaseCommand):
    help = (
        'Show the configured database, test the connection, and list applied/pending '
        'migrations. Never prints the password.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--database', default=DEFAULT_DB_ALIAS,
            help='Database alias from settings.DATABASES (default: "default").',
        )

    def handle(self, *args, **options):
        alias = options['database']
        try:
            connection = connections[alias]
        except ImproperlyConfigured as exc:
            raise CommandError(f'{exc}\nHint: run  python -m pip install -r requirements.txt') from exc
        conf = connection.settings_dict
        is_postgres = connection.vendor == 'postgresql'

        self.section('Configuration')
        self.row('Engine', conf['ENGINE'])
        if is_postgres:
            db_options = conf.get('OPTIONS', {})
            self.row('Host', conf['HOST'] or 'localhost (default)')
            self.row('Port', conf['PORT'] or '5432')
            self.row('Database', conf['NAME'])
            self.row('User', conf['USER'])
            self.row('Password', 'set (hidden)' if conf['PASSWORD'] else 'not set')
            self.row('sslmode', db_options.get('sslmode', 'prefer (libpq default)'))
            self.row('Timeout', f"{db_options.get('connect_timeout', 'none')}s")
        else:
            path = Path(conf['NAME'])
            self.row('File', f'{path}' if path.exists() else f'{path} (does not exist yet)')

        started = time.monotonic()
        try:
            connection.ensure_connection()
        except DatabaseError as exc:
            elapsed = time.monotonic() - started
            self.stdout.flush()  # show the configuration above the error
            raise CommandError(self.failure_message(conf, is_postgres, exc, elapsed)) from exc
        elapsed = time.monotonic() - started

        self.section('Server')
        self.row('Connected', self.style.SUCCESS(f'yes ({elapsed * 1000:.0f} ms)'))
        if is_postgres:
            self.show_postgres_server(connection, conf)
        else:
            self.row('Version', f'SQLite {sqlite3.sqlite_version}')

        self.show_migrations(connection)
        self.show_scam_count(connection, alias)

    # -- output helpers -----------------------------------------------------

    def section(self, title):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(title))

    def row(self, label, value):
        self.stdout.write(f'  {label + ":":<14} {value}')

    # -- sections -----------------------------------------------------------

    def show_postgres_server(self, connection, conf):
        with connection.cursor() as cursor:
            cursor.execute('SHOW server_version')
            self.row('Version', f'PostgreSQL {cursor.fetchone()[0]}')
            cursor.execute(
                'SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid = pg_backend_pid()'
            )
            ssl_row = cursor.fetchone()

        if ssl_row and ssl_row[0]:
            self.row('SSL in use', self.style.SUCCESS(f'yes ({ssl_row[1]}, {ssl_row[2]})'))
        elif (conf['HOST'] or '').lower() in LOCAL_HOSTS:
            self.row('SSL in use', 'no (local connection)')
        else:
            self.row('SSL in use', self.style.WARNING(
                'no - traffic to the database is NOT encrypted. Enable ssl on the server '
                'and set POSTGRES_SSLMODE=require.'
            ))

    def show_migrations(self, connection):
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        applied = loader.applied_migrations
        per_app = {}
        for key in loader.graph.nodes:
            done, pending = per_app.setdefault(key[0], ([], []))
            (done if key in applied else pending).append(key[1])

        self.section('Migrations')
        total_pending = 0
        for app_label in sorted(per_app):
            done, pending = per_app[app_label]
            total_pending += len(pending)
            line = f'{len(done)} applied, {len(pending)} unapplied'
            if pending:
                pending.sort()
                names = ', '.join(pending) if len(pending) <= 3 else f'{pending[0]} ... {pending[-1]}'
                line = self.style.WARNING(f'{line}  ({names})')
            self.row(app_label, line)

        if total_pending:
            self.stdout.write(self.style.WARNING(
                f'  {total_pending} unapplied migration(s). Run: python manage.py migrate'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('  All migrations are applied.'))

    def show_scam_count(self, connection, alias):
        scam_model = apps.get_model('scams', 'Scam')
        table = scam_model._meta.db_table
        self.section('Data')
        if table in connection.introspection.table_names():
            self.row(table, f'{scam_model.objects.using(alias).count()} rows')
        else:
            self.row(table, 'table does not exist yet (run: python manage.py migrate)')

    # -- failure ------------------------------------------------------------

    def failure_message(self, conf, is_postgres, exc, elapsed):
        error = str(exc).strip() or exc.__class__.__name__
        too_old = UNSUPPORTED_VERSION.search(error) if isinstance(exc, NotSupportedError) else None
        if too_old:
            return self.unsupported_version_message(is_postgres, error, too_old['minimum'])

        lines = [f'Could not connect to the database after {elapsed:.1f}s.', f'  {error}', '']

        if not is_postgres:
            lines.append(
                f'Check that the folder for {conf["NAME"]} exists and is writable '
                '(set SQLITE_PATH in .env to use a different file).'
            )
            return '\n'.join(lines)

        lowered = error.lower()
        hint = next(
            (hint for needles, hint in FAILURE_HINTS if any(n in lowered for n in needles)),
            None,
        )
        port = conf['PORT'] or '5432'
        if hint:
            lines.extend(['Most likely cause:', f'  {hint.format(port=port)}', ''])
        lines.append('Checklist:')
        lines.extend(f'  - {item.format(port=port)}' for item in CHECKLIST)
        return '\n'.join(lines)

    def unsupported_version_message(self, is_postgres, error, minimum):
        """The server answered (network, login and SSL are fine) but is too old for this Django."""
        lines = [
            f'Connected, but Django {django.get_version()} does not support this database server:',
            f'  {error}',
            '',
            'Fix:',
        ]
        if is_postgres:
            lines.append(
                f'  Upgrade PostgreSQL on the VM to {minimum} or newer. Debian 11 and Ubuntu 20.04 '
                'ship an older version: add the PostgreSQL apt repository (PGDG), install a current '
                'version and move the data across with pg_upgradecluster. '
                'Step by step: docs/POSTGRES.md, section 1.1.'
            )
        else:
            lines.append(
                f'  This Python uses SQLite {sqlite3.sqlite_version}. Use a Python that comes with '
                f'SQLite {minimum} or newer (the python.org installers and conda include one).'
            )
        return '\n'.join(lines)
