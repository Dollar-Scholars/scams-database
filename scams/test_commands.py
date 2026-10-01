"""Tests for the management commands (db_status, backup_db) and the database settings."""
import io
import os
import runpy
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import NotSupportedError, OperationalError
from django.test import SimpleTestCase
from dotenv import dotenv_values

from .management.commands import db_status
from .management.commands.backup_db import MAX_KEEP_DAYS, Command as BackupCommand
from .management.commands.db_status import Command as DbStatusCommand

SETTINGS_FILE = Path(settings.BASE_DIR) / 'scam_project' / 'settings.py'
POSTGRES_CONF = {'ENGINE': 'django.db.backends.postgresql', 'HOST': 'db.example', 'PORT': '5432', 'NAME': 'scams'}


def hint_for(message):
    """The "Most likely cause" line db_status prints for a driver error message, or None."""
    exc = OperationalError(message)
    lines = DbStatusCommand().failure_message(POSTGRES_CONF, True, exc, 0.1).splitlines()
    if 'Most likely cause:' not in lines:
        return None
    return lines[lines.index('Most likely cause:') + 1].strip()


class DbStatusHintTests(SimpleTestCase):

    def test_dns_failures_get_the_dns_hint(self):
        for message in (
            # psycopg 3 on Windows and Linux; the host names contain other hints' needles.
            "failed to resolve host 'ssl-db.internal': [Errno 11001] getaddrinfo failed",
            "failed to resolve host 'certificate-db': [Errno -2] Name or service not known",
            'could not translate host name "ssl.example" to address: Name or service not known',
        ):
            with self.subTest(message=message):
                self.assertIn('POSTGRES_HOST could not be resolved', hint_for(message))

    def test_ssl_errors_still_get_the_ssl_hint(self):
        self.assertIn('SSL negotiation failed', hint_for('server does not support SSL, but SSL was required'))

    def test_connection_refused_hint_names_the_cluster_unit(self):
        hint = hint_for('connection to server at "10.0.0.5", port 5432 failed: Connection refused')
        self.assertIn('pg_lsclusters', hint)
        self.assertIn('sudo systemctl status postgresql@<version>-main', hint)
        self.assertIn('sudo journalctl -u postgresql@<version>-main', hint)

    def test_unknown_error_has_no_hint_but_a_checklist(self):
        message = DbStatusCommand().failure_message(POSTGRES_CONF, True, OperationalError('boom'), 0.1)
        self.assertNotIn('Most likely cause:', message)
        self.assertIn('Checklist:', message)

    def test_too_old_postgresql_says_to_upgrade_the_server(self):
        """Django 5.2 connects, then refuses PostgreSQL < 14 with NotSupportedError."""
        connection = mock.Mock(vendor='postgresql', settings_dict={
            **POSTGRES_CONF, 'USER': 'scams_app', 'PASSWORD': 'hunter2', 'OPTIONS': {'sslmode': 'require'},
        })
        connection.ensure_connection.side_effect = NotSupportedError(
            'PostgreSQL 14 or later is required (found 13.16).'
        )
        stdout = io.StringIO()
        with mock.patch.object(db_status, 'connections', {'default': connection}):
            with self.assertRaises(CommandError) as ctx:
                call_command('db_status', stdout=stdout)
        message = str(ctx.exception)
        self.assertIn('PostgreSQL 14 or later is required (found 13.16).', message)
        self.assertIn('Upgrade PostgreSQL on the VM to 14 or newer', message)
        self.assertIn('PGDG', message)
        self.assertNotIn('Could not connect', message)
        self.assertNotIn('Checklist:', message)
        self.assertIn('db.example', stdout.getvalue())  # the configuration is still shown
        self.assertNotIn('hunter2', stdout.getvalue() + message)

    def test_other_not_supported_errors_get_the_connection_checklist(self):
        message = DbStatusCommand().failure_message(
            POSTGRES_CONF, True, NotSupportedError('feature not supported'), 0.1
        )
        self.assertIn('Could not connect', message)
        self.assertIn('Checklist:', message)


class PostgresSettingsTests(SimpleTestCase):

    def load_settings(self, **env):
        """Run settings.py in a fresh namespace with PostgreSQL configured by `env`."""
        values = {
            'DJANGO_DEBUG': 'True', 'DJANGO_SECRET_KEY': 'x',
            'POSTGRES_HOST': 'db.example', 'POSTGRES_DB': 'scams', 'POSTGRES_USER': 'scams_app',
            'POSTGRES_SSLMODE': '',
            **env,
        }
        with mock.patch.dict(os.environ, values):
            return runpy.run_path(str(SETTINGS_FILE))

    def test_invalid_sslmode_lists_the_allowed_values(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.load_settings(POSTGRES_SSLMODE='requre')
        self.assertIn("'requre'", str(ctx.exception))
        self.assertIn('disable, allow, prefer, require, verify-ca, verify-full', str(ctx.exception))

    def test_valid_sslmode_is_passed_to_the_driver(self):
        for mode in ('disable', 'require', 'verify-full'):
            with self.subTest(mode=mode):
                options = self.load_settings(POSTGRES_SSLMODE=mode)['DATABASES']['default']['OPTIONS']
                self.assertEqual(options['sslmode'], mode)
        self.assertEqual(self.load_settings()['DATABASES']['default']['OPTIONS']['sslmode'], 'prefer')

    def test_env_file_is_read_without_variable_expansion(self):
        with mock.patch('dotenv.load_dotenv') as load_dotenv:
            self.load_settings()
        self.assertEqual(load_dotenv.call_args.kwargs, {'override': False, 'interpolate': False})
        # The quoting advice in .env.example and docs/POSTGRES.md, read the same way.
        env_file = io.StringIO(r"POSTGRES_PASSWORD='it\'s a#b ${HOME}\\x'" + '\n')
        self.assertEqual(dotenv_values(stream=env_file, interpolate=False)['POSTGRES_PASSWORD'],
                         "it's a#b ${HOME}\\x")


class BackupKeepDaysTests(SimpleTestCase):

    def test_out_of_range_keep_days_fails_before_anything_is_written(self):
        """Regression: a huge value raised OverflowError in prune(), after the backup was written."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / 'backups'
            for keep_days in (-1, MAX_KEEP_DAYS + 1, 10 ** 12):
                with self.subTest(keep_days=keep_days):
                    with self.assertRaisesMessage(CommandError, f'between 0 and {MAX_KEEP_DAYS}'):
                        call_command('backup_db', keep_days=keep_days, output_dir=str(output_dir), stdout=io.StringIO())
            with mock.patch.dict(os.environ, {'BACKUP_KEEP_DAYS': '99999999999'}):
                with self.assertRaisesMessage(CommandError, 'BACKUP_KEEP_DAYS'):
                    call_command('backup_db', output_dir=str(output_dir), stdout=io.StringIO())
            self.assertFalse(output_dir.exists())

    def test_largest_keep_days_prunes_without_overflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'db_20200101-000000.sqlite3').touch()
            BackupCommand(stdout=io.StringIO()).prune(Path(tmp), 'db', '.sqlite3', MAX_KEEP_DAYS)
            self.assertTrue((Path(tmp) / 'db_20200101-000000.sqlite3').exists())
