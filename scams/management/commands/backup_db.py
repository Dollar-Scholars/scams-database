"""
python manage.py backup_db [--output-dir DIR] [--keep-days N] [--copy-to user@host:/path/ ...]

PostgreSQL: runs pg_dump in custom format (-Fc) -> <db>_<YYYYmmdd-HHMMSS>.dump
SQLite:     consistent copy via the sqlite3 backup API -> <name>_<YYYYmmdd-HHMMSS>.sqlite3

Optionally copies the new file to other machines with scp, then deletes this
command's own backups older than --keep-days. Nothing is deleted if any step fails.
"""

import os
import re
import shutil
import sqlite3
import subprocess
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections

STAMP_FORMAT = '%Y%m%d-%H%M%S'
STAMP_PATTERN = r'\d{8}-\d{6}'
# 100 years. A huge value would overflow the date maths in prune(), after the backup was written.
MAX_KEEP_DAYS = 36500


def env_int(name, default):
    value = os.environ.get(name, '').strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        raise CommandError(f'{name} must be a whole number, got {value!r}.') from None


class Command(BaseCommand):
    help = (
        'Back up the configured database (pg_dump -Fc for PostgreSQL, a file copy for '
        'SQLite), optionally scp it elsewhere, and prune old backups made by this command.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default=os.environ.get('BACKUP_DIR', '').strip() or str(settings.BASE_DIR / 'backups'),
            help='Folder for backup files (default: $BACKUP_DIR or ./backups).',
        )
        parser.add_argument(
            '--keep-days', type=int, default=None,
            help='Delete backups made by this command that are older than N days; '
                 '0 keeps everything (default: $BACKUP_KEEP_DAYS or 14).',
        )
        parser.add_argument(
            '--copy-to', action='append', default=None, metavar='USER@HOST:/PATH/',
            help='scp destination for the new backup; repeat for several '
                 '(default: comma-separated $BACKUP_REMOTE_TARGETS). Needs SSH key login.',
        )
        parser.add_argument(
            '--database', default=DEFAULT_DB_ALIAS,
            help='Database alias from settings.DATABASES (default: "default").',
        )

    def handle(self, *args, **options):
        try:
            self.backup(options)
        finally:
            self.stdout.flush()  # progress lines before any error message

    def backup(self, options):
        keep_days = options['keep_days']
        if keep_days is None:
            keep_days = env_int('BACKUP_KEEP_DAYS', 14)
        if not 0 <= keep_days <= MAX_KEEP_DAYS:
            raise CommandError(
                f'--keep-days (or BACKUP_KEEP_DAYS) must be between 0 and {MAX_KEEP_DAYS}, got {keep_days}.'
            )

        targets = options['copy_to']
        if targets is None:
            targets = [
                t.strip() for t in os.environ.get('BACKUP_REMOTE_TARGETS', '').split(',') if t.strip()
            ]

        output_dir = Path(options['output_dir']).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        connection = connections[options['database']]
        conf = connection.settings_dict
        stamp = datetime.now().strftime(STAMP_FORMAT)

        if connection.vendor == 'postgresql':
            base, suffix = re.sub(r'[^A-Za-z0-9_.-]', '_', conf['NAME']), '.dump'
            backup_path = output_dir / f'{base}_{stamp}{suffix}'
            self.dump_postgres(conf, backup_path)
            restore_hint = (
                'pg_restore --clean --if-exists '
                f'--host={conf["HOST"] or "localhost"} --port={conf["PORT"] or "5432"} '
                f'--username={conf["USER"]} --dbname={conf["NAME"]} "{backup_path}"'
            )
        elif connection.vendor == 'sqlite':
            source = Path(conf['NAME'])
            base, suffix = source.stem, '.sqlite3'
            backup_path = output_dir / f'{base}_{stamp}{suffix}'
            self.copy_sqlite(source, backup_path)
            restore_hint = (
                f'stop the server, then copy "{backup_path}" over "{source}" '
                '(or point SQLITE_PATH at the backup)'
            )
        else:
            raise CommandError(f'backup_db does not support the {connection.vendor} backend.')

        size_kb = backup_path.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(f'Backup written: {backup_path} ({size_kb:,.1f} KB)'))

        failed = self.copy_to_targets(backup_path, targets)
        if failed:
            raise CommandError(
                f'Backup saved locally at {backup_path}, but copying failed for: '
                f'{", ".join(failed)}. Old backups were not pruned.'
            )

        self.prune(output_dir, base, suffix, keep_days)
        self.stdout.write(f'To restore: {restore_hint}')

    # -- PostgreSQL ---------------------------------------------------------

    def dump_postgres(self, conf, backup_path):
        configured = os.environ.get('PG_DUMP', '').strip()
        pg_dump = shutil.which(configured or 'pg_dump')
        if not pg_dump:
            where = f'PG_DUMP={configured} does not exist' if configured else 'pg_dump is not on PATH'
            raise CommandError(
                f'{where}. Install the PostgreSQL client tools (the same or a newer major '
                'version than the server) and put pg_dump on PATH, or set PG_DUMP to its '
                'full path, e.g. PG_DUMP=C:/Program Files/PostgreSQL/16/bin/pg_dump.exe'
            )

        version = subprocess.run([pg_dump, '--version'], capture_output=True, text=True)
        self.stdout.write(f'Using {version.stdout.strip() or pg_dump}')

        db_options = conf.get('OPTIONS', {})
        env = os.environ.copy()
        # The password only ever travels through the child's environment, never argv.
        if conf['PASSWORD']:
            env['PGPASSWORD'] = conf['PASSWORD']
        if db_options.get('sslmode'):
            env['PGSSLMODE'] = str(db_options['sslmode'])
        if db_options.get('connect_timeout'):
            env['PGCONNECT_TIMEOUT'] = str(db_options['connect_timeout'])

        partial = backup_path.with_name(backup_path.name + '.partial')
        cmd = [
            pg_dump, '--format=custom', '--no-password',
            f'--host={conf["HOST"] or "localhost"}',
            f'--port={conf["PORT"] or "5432"}',
            f'--username={conf["USER"]}',
            f'--file={partial}',
            f'--dbname={conf["NAME"]}',
        ]
        self.stdout.write(f'Dumping {conf["NAME"]} from {conf["HOST"]}:{conf["PORT"] or "5432"} ...')
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                raise CommandError(self.pg_dump_error(result.stderr))
            partial.replace(backup_path)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise

    def pg_dump_error(self, stderr):
        message = f'pg_dump failed:\n  {stderr.strip() or "(no output)"}'
        if 'version mismatch' in stderr:
            message += (
                '\nYour pg_dump is older than the server. Install client tools of the same or a '
                'newer major version and set PG_DUMP to that pg_dump.'
            )
        else:
            message += '\nRun  python manage.py db_status  to diagnose the connection.'
        return message

    # -- SQLite -------------------------------------------------------------

    def copy_sqlite(self, source, backup_path):
        if not source.is_file():
            raise CommandError(f'SQLite database not found: {source}')
        partial = backup_path.with_name(backup_path.name + '.partial')
        # Read-only URI: the source database is never modified.
        source_uri = source.resolve().as_uri() + '?mode=ro'
        try:
            with closing(sqlite3.connect(source_uri, uri=True)) as src, \
                    closing(sqlite3.connect(partial)) as dst:
                src.backup(dst)
            partial.replace(backup_path)
        except BaseException as exc:
            partial.unlink(missing_ok=True)
            if isinstance(exc, sqlite3.Error):
                raise CommandError(f'SQLite backup failed: {exc}') from exc
            raise

    # -- copy & prune -------------------------------------------------------

    def copy_to_targets(self, backup_path, targets):
        if not targets:
            return []
        scp = shutil.which('scp')
        if not scp:
            raise CommandError(
                f'Backup saved locally at {backup_path}, but scp was not found on PATH '
                '(Windows: Settings > Optional features > OpenSSH Client).'
            )
        failed = []
        for target in targets:
            self.stdout.write(f'Copying to {target} ...')
            result = subprocess.run(
                [scp, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
                 '--', str(backup_path), target],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS(f'  copied to {target}'))
            else:
                failed.append(target)
                detail = result.stderr.strip() or f'exit code {result.returncode}'
                self.stderr.write(f'  FAILED {target}: {detail}')
        return failed

    def prune(self, output_dir, base, suffix, keep_days):
        if keep_days == 0:
            return
        own_backup = re.compile(rf'^{re.escape(base)}_({STAMP_PATTERN}){re.escape(suffix)}$')
        cutoff = datetime.now() - timedelta(days=keep_days)
        removed = 0
        for path in output_dir.iterdir():
            match = own_backup.match(path.name)
            if not match or not path.is_file():
                continue
            try:
                made_at = datetime.strptime(match.group(1), STAMP_FORMAT)
            except ValueError:
                continue
            if made_at < cutoff:
                path.unlink()
                removed += 1
                self.stdout.write(f'Pruned old backup: {path.name}')
        if removed:
            self.stdout.write(f'Removed {removed} backup(s) older than {keep_days} days.')
