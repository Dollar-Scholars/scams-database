# Running the Scams DB on PostgreSQL

By default the app uses SQLite (`db.sqlite3`), so volunteers need no database
setup. To use a PostgreSQL server instead (for example a Linux VM), you only set
environment variables: as soon as `POSTGRES_HOST` is set, Django switches to
PostgreSQL. Nothing in the code changes.

- **VM side** commands are for a Debian/Ubuntu server (bash).
- **App side** commands are for Windows PowerShell, run in the folder that
  contains `manage.py`, with your venv or conda env activated.

Contents: [VM setup](#1-vm-side-set-up-postgresql) ·
[Connect the app](#2-app-side-connect-the-app) ·
[Move existing SQLite data](#3-move-existing-sqlite-data) ·
[Backups and restore](#4-backups-and-restore) ·
[Troubleshooting](#5-troubleshooting)

---

## 1. VM side: set up PostgreSQL

The examples use these addresses; replace them with your own:

| Machine | Example IP | How to find it |
| --- | --- | --- |
| PostgreSQL VM | `192.168.1.50` | on the VM: `ip -4 addr` |
| Your Windows PC (the client) | `192.168.1.20` | PowerShell: `ipconfig` |

If the VM sits behind NAT (VirtualBox/Hyper-V default switch), the address the
server sees may differ from `ipconfig`. The server's "no pg_hba.conf entry for
host ..." error always shows the exact address to use.

### 1.1 Install PostgreSQL 14 or newer

Django 5.2 requires PostgreSQL 14+. Debian 12+ and Ubuntu 22.04+ ship a new
enough version:

```bash
sudo apt update
sudo apt install -y postgresql
psql --version                          # must be 14 or higher
sudo systemctl enable --now postgresql
```

Debian 11 and Ubuntu 20.04 ship PostgreSQL 13 and 12, which Django 5.2 refuses
(`db_status` says `PostgreSQL 14 or later is required (found 13.x)`). Install a
current version from the PostgreSQL apt repository (PGDG) instead:

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh   # adds the PGDG repository
sudo apt install -y postgresql-18
```

If the old version already holds the app's data, back it up (section 4), then
move it across. The install above created an empty `18 main` cluster; drop it,
then upgrade the old cluster, which copies the databases, roles, configuration
(`postgresql.conf`, `pg_hba.conf`) and port to a new `18 main`:

```bash
pg_lsclusters                          # e.g. 13 main on 5432, 18 main on 5433
sudo pg_dropcluster --stop 18 main     # the new, empty cluster
sudo pg_upgradecluster 13 main         # 13 -> 18; the old cluster moves to another port
pg_lsclusters                          # 18 main now on 5432
```

Once `python manage.py db_status` on your PC shows `PostgreSQL 18.x` and the
app works, remove the old cluster: `sudo pg_dropcluster 13 main`.

### 1.2 Create a role and a database (least privilege)

The app gets its own login role that owns only its own database. It is not a
superuser and cannot create roles or other databases.

```bash
# prints a random password you can paste into .env later
openssl rand -hex 24
sudo -u postgres psql
```

```sql
CREATE ROLE scams_app WITH LOGIN PASSWORD 'paste-the-random-password-here';
CREATE DATABASE scams OWNER scams_app ENCODING 'UTF8';

-- Nobody else may connect to this database
REVOKE CONNECT ON DATABASE scams FROM PUBLIC;
GRANT CONNECT ON DATABASE scams TO scams_app;

-- ONLY if you want to run `python manage.py test` against this server
-- (Django creates and drops a temporary test_scams database):
-- ALTER ROLE scams_app CREATEDB;

\q
```

Because `scams_app` owns the database, it can create tables in the `public`
schema, which `migrate` needs (on PostgreSQL 15+ only the database owner can).

### 1.3 Listen on the network: `postgresql.conf`

```bash
sudo -u postgres psql -c 'SHOW config_file;'
sudo nano /etc/postgresql/16/main/postgresql.conf   # use the path printed above
```

Set (uncomment) these lines:

```ini
listen_addresses = 'localhost,192.168.1.50'   # or '*' for all interfaces
port = 5432
ssl = on                                      # Debian/Ubuntu ship a self-signed cert, so this works out of the box
```

`listen_addresses` needs a **restart** (a reload is not enough):

```bash
sudo systemctl restart postgresql
sudo ss -tlnp | grep 5432      # should show 192.168.1.50:5432 (or 0.0.0.0:5432)
```

### 1.4 Allow your PC: `pg_hba.conf`

```bash
sudo -u postgres psql -c 'SHOW hba_file;'
sudo nano /etc/postgresql/16/main/pg_hba.conf      # use the path printed above
```

Add one line at the end. `hostssl` refuses unencrypted connections;
`scram-sha-256` is the modern password method. Allow only your PC's address (`/32`):

```text
# TYPE   DATABASE  USER       ADDRESS           METHOD
hostssl  scams     scams_app  192.168.1.20/32   scram-sha-256
```

If you gave the role `CREATEDB` to run tests there, use
`scams,test_scams,postgres` in the DATABASE column (Django's test runner connects
to the `postgres` database to create `test_scams`).

`pg_hba.conf` changes only need a **reload**:

```bash
sudo systemctl reload postgresql
```

### 1.5 Open the firewall

With ufw, allow port 5432 from your PC only:

```bash
sudo ufw allow from 192.168.1.20 to any port 5432 proto tcp
sudo ufw status
```

firewalld (RHEL/Fedora) equivalent:

```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.20/32" port port="5432" protocol="tcp" accept'
sudo firewall-cmd --reload
```

Also check any firewall or port forwarding in the hypervisor or cloud provider.
Never expose 5432 to the whole internet.

### 1.6 SSL

- `ssl = on` plus `hostssl` in `pg_hba.conf` and `POSTGRES_SSLMODE=require` in
  `.env` means traffic is always encrypted. This is the recommended minimum.
- `require` does not check the server's certificate. To guard against
  impersonation, give the server a certificate from your own CA, copy the CA cert
  to the PC, and use `POSTGRES_SSLMODE=verify-full` (libpq reads the CA from
  `%APPDATA%\postgresql\root.crt`).
- `python manage.py db_status` shows `SSL in use: yes (TLSv1.3, ...)` when it works.

---

## 2. App side: connect the app

Check the network path first. `TcpTestSucceeded : True` means the firewall and
`listen_addresses` are fine:

```powershell
Test-NetConnection 192.168.1.50 -Port 5432
```

Install the requirements (includes the `psycopg` driver), then create `.env`:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

In `.env`, uncomment and fill the PostgreSQL block:

```ini
DJANGO_DEBUG=True
POSTGRES_HOST=192.168.1.50
POSTGRES_PORT=5432
POSTGRES_DB=scams
POSTGRES_USER=scams_app
POSTGRES_PASSWORD=paste-the-random-password-here
POSTGRES_SSLMODE=require
```

> Moving existing data from SQLite? Do step 3.1 (dump) **before** filling in
> `POSTGRES_HOST`, because once it is set every command talks to PostgreSQL.

Then:

```powershell
python manage.py db_status          # connection, server version, SSL, pending migrations
python manage.py migrate            # creates the tables on the server
python manage.py db_status          # should say "All migrations are applied."
python manage.py createsuperuser    # skip if you are importing users in step 3
python manage.py runserver
```

`db_status` never prints the password. If it cannot connect it exits with an
error, the most likely cause and a checklist (see [Troubleshooting](#5-troubleshooting)).

Other settings that matter on a server (all optional, see `.env.example`):
`POSTGRES_CONNECT_TIMEOUT` (default 10 s), `POSTGRES_CONN_MAX_AGE` (default 60 s
connection reuse), `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and a real
`DJANGO_SECRET_KEY` with `DJANGO_DEBUG=False`.

To go back to SQLite, comment out `POSTGRES_HOST` in `.env`.

### 2.1 Serving the site with debug off

When the app runs for real (not just on your PC), set `DJANGO_DEBUG=False` in
`.env`, plus a real `DJANGO_SECRET_KEY` and the host name(s) in
`DJANGO_ALLOWED_HOSTS`. With debug off, Django no longer serves the CSS, JS and
logo files itself; WhiteNoise serves them from the `collectstatic` folder, so run
this after every deploy that changes files under `scams/static/` or upgrades
Django (the admin's own CSS and JS change between Django versions):

```powershell
python manage.py collectstatic --noinput   # copies static files into ./staticfiles
python manage.py check --deploy            # security checklist for the settings above
```

Plain-HTTP test box only: set `DJANGO_SESSION_COOKIE_SECURE=False` and
`DJANGO_CSRF_COOKIE_SECURE=False`, or the report form cannot be submitted.
Behind a reverse proxy that terminates HTTPS (nginx, Caddy, ...), Django itself only
sees plain HTTP. Before turning on `DJANGO_SECURE_SSL_REDIRECT`, set
`DJANGO_SECURE_PROXY_SSL_HEADER=True` (the proxy must always overwrite
`X-Forwarded-Proto`, e.g. nginx `proxy_set_header X-Forwarded-Proto $scheme;`, never
pass on the client's value) and put the public origin, e.g.
`https://scams.example.org`, in `DJANGO_CSRF_TRUSTED_ORIGINS`. Otherwise every page
redirects to itself forever and the report form fails with 403 (CSRF verification failed).
Once HTTPS works, turn on `DJANGO_SECURE_SSL_REDIRECT=True` and
`DJANGO_SECURE_HSTS_SECONDS` (start with 3600); `check --deploy` warns (W004, W008)
until you do. The W005/W021 warnings that follow (HSTS for subdomains, preload
list) are expected: those settings affect every subdomain of your domain, so they
are deliberately not configurable here.
The dashboard loads Chart.js from cdn.jsdelivr.net, so visitors' browsers need
access to that site for the charts (the numbers tables work without it).

---

## 3. Move existing SQLite data

These exact commands were rehearsed against a copy of the project's `db.sqlite3`
(PostgreSQL 18). The row counts, IDs, users, groups, permissions and admin
history all matched after the import.

### 3.1 Dump from SQLite (while `POSTGRES_HOST` is still unset)

```powershell
python manage.py db_status          # Engine must be django.db.backends.sqlite3
python manage.py migrate            # SQLite schema up to date
New-Item -ItemType Directory -Force backups | Out-Null
python -X utf8 manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude sessions --indent 2 --output backups\sqlite_data.json
```

- The dump contains reporters' names, emails and phone numbers and the admin
  users' password hashes. It goes into the git-ignored `backups` folder so that
  `git add .` can never pick it up; delete it after step 3.2.
- `-X utf8` is required on Windows. Without it `dumpdata` writes the file in the
  Windows code page and `loaddata` fails on any accented character. Do not use
  `> file.json` either: PowerShell 5.1 would write UTF-16.
- Content types and permissions are excluded because `migrate` recreates them on
  PostgreSQL; the natural-key flags let users, groups and admin history point at
  the new ones.
- If your SQLite file is not `db.sqlite3`, set `SQLITE_PATH` in `.env` first.

### 3.2 Load into PostgreSQL

Now fill in the `POSTGRES_*` lines in `.env` (section 2), then:

```powershell
python manage.py db_status          # Engine must be django.db.backends.postgresql
python manage.py migrate
python -X utf8 manage.py loaddata backups\sqlite_data.json
python manage.py db_status          # the scams_scam row count must match SQLite
Remove-Item backups\sqlite_data.json
```

Delete `backups\sqlite_data.json` whether or not the import succeeded (if it
failed, fix the cause and dump again): it holds reporters' personal details and
password hashes.

`loaddata` also resets the ID sequences, so new reports continue after the highest
imported ID. Load into a freshly migrated, empty database.

If `loaddata` fails with `value too long for type character varying(2)`: SQLite
does not enforce field lengths, PostgreSQL does. For example, the old
`my_script.py` stored `"Switzerland"` in the 2-letter country field. List the bad
rows while still on SQLite, fix them (e.g. in the admin), and dump again:

```powershell
python manage.py shell -c "from django.db.models.functions import Length; from scams.models import Scam; print(list(Scam.objects.annotate(n=Length('country')).filter(n__gt=2).values_list('id', 'country')))"
```

---

## 4. Backups and restore

`python manage.py backup_db` backs up whichever database is configured:

- **PostgreSQL:** `pg_dump` custom format to `backups\<db>_<YYYYmmdd-HHMMSS>.dump`.
  The password is passed to `pg_dump` only through its environment (`PGPASSWORD`),
  never on the command line. A failed dump leaves no partial file behind.
- **SQLite:** a consistent copy made with SQLite's backup API, safe while the
  server is running, to `backups\db_<YYYYmmdd-HHMMSS>.sqlite3`.

```powershell
python manage.py backup_db                                    # to .\backups, prune after 14 days
python manage.py backup_db --output-dir D:\scams-backups --keep-days 30
python manage.py backup_db --keep-days 0                      # never delete old backups
python manage.py backup_db --copy-to backup@192.168.1.60:/srv/backups/scams/ --copy-to backup@nas:/volume1/scams/
```

- **pg_dump on Windows:** install the PostgreSQL command-line tools with the
  **same or a newer major version** than the server (the EDB installer lets you
  choose "Command Line Tools" only). If `pg_dump` is not on `PATH`, set it in `.env`
  with forward slashes: `PG_DUMP=C:/Program Files/PostgreSQL/16/bin/pg_dump.exe`.
- **Pruning** deletes only files this command created for this database (names
  matching `<db>_<YYYYmmdd-HHMMSS>.dump`) that are older than `--keep-days`. Other
  files in the folder are never touched. Nothing is pruned if a step failed.
- **`--copy-to`** (or `BACKUP_REMOTE_TARGETS=a,b` in `.env`) runs `scp` once per
  target. It exits with an error if any copy fails. `scp` runs non-interactively,
  so set up key login first (`ssh-keygen`, then add the public key to the
  target's `~/.ssh/authorized_keys`), and `ssh` to each target once by hand to
  accept its host key.
- Defaults can live in `.env`: `BACKUP_DIR`, `BACKUP_KEEP_DAYS`,
  `BACKUP_REMOTE_TARGETS`, `PG_DUMP`.

Example: daily backups with Windows Task Scheduler (adjust the paths; run
`backup_db` once by hand first to make sure it works):

```powershell
$action  = New-ScheduledTaskAction -Execute "C:\path\to\scams-database\.venv\Scripts\python.exe" -Argument "manage.py backup_db" -WorkingDirectory "C:\path\to\scams-database"
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "Scams DB backup" -Action $action -Trigger $trigger
```

### Restore

Stop the app first. `backup_db` prints the exact command after each backup. It
has this form and asks for the password:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\pg_restore.exe" --clean --if-exists --host=192.168.1.50 --port=5432 --username=scams_app --dbname=scams "backups\scams_20260927-130537.dump"
```

`--clean --if-exists` drops every table, sequence and index contained in the dump
and recreates it with the backed-up data. To check a dump without
restoring it, run `pg_restore --list <file>`. To restore into a database owned by
a different role, add `--no-owner`.

For SQLite: stop the server and copy the backup file over `db.sqlite3` (or point
`SQLITE_PATH` at it).

---

## 5. Troubleshooting

Run `python manage.py db_status` first: it shows the host, port, database, user
and sslmode Django is really using, and a hint for the error it got.

| Error | Cause | Fix |
| --- | --- | --- |
| `Connection refused` | Nothing listens on that IP/port: service down, `listen_addresses` still `localhost`, wrong `POSTGRES_PORT`. | VM: `pg_lsclusters` or `sudo systemctl status postgresql@<version>-main` (the plain `postgresql` unit is only an umbrella on Debian/Ubuntu), logs with `sudo journalctl -u postgresql@<version>-main`; `sudo ss -tlnp \| grep 5432`; fix `listen_addresses` and **restart**. |
| `connection timeout expired` | Packets are dropped: VM firewall, hypervisor/cloud firewall, wrong IP, VM off. On Windows a refused port can also show up as a timeout. | `Test-NetConnection <vm-ip> -Port 5432`; `sudo ufw allow from <pc-ip> to any port 5432 proto tcp`; check `POSTGRES_HOST`. Lower `POSTGRES_CONNECT_TIMEOUT` to fail faster. |
| `no pg_hba.conf entry for host "X", user "...", database "...", no encryption` / `SSL encryption` | The server is reachable but has no rule for this client. `no encryption` with a `hostssl` rule means the client did not use SSL. | Add `hostssl scams scams_app X/32 scram-sha-256` using the exact X from the message, then `sudo systemctl reload postgresql`. With `no encryption`, set `POSTGRES_SSLMODE=require`. |
| `password authentication failed for user "scams_app"` | Wrong user/password, a typo or stray quote in `.env`, or the password is still stored as md5 (set on PostgreSQL 13 or older and kept by an upgrade). | `ALTER ROLE scams_app WITH PASSWORD '...';` (PostgreSQL 14+ stores it as SCRAM). In `.env`, prefer a password without quotes, spaces or `#` (e.g. from `openssl rand -hex 24`). Otherwise wrap it in single quotes and write a `'` inside it as `\'` and a `\` as `\\`: `POSTGRES_PASSWORD='it\'s a#b'`. |
| `server does not support SSL, but SSL was required` | `ssl = off` on the server while `POSTGRES_SSLMODE=require`. | Set `ssl = on` in `postgresql.conf` and restart (Debian/Ubuntu have a default cert). Use `prefer`/`disable` only on a trusted network. |
| `certificate verify failed` / `root certificate file ... does not exist` | `verify-ca`/`verify-full` without the CA cert on the PC, or the hostname does not match the cert. | Put the CA cert at `%APPDATA%\postgresql\root.crt` and connect with the name in the cert, or use `POSTGRES_SSLMODE=require`. |
| `PostgreSQL 14 or later is required (found 13.x)` (`NotSupportedError`) | The connection works, but Django 5.2 does not support PostgreSQL 13 or older. | Upgrade PostgreSQL on the VM to 14 or newer: section 1.1 (PGDG repository, then `pg_upgradecluster`). |
| `permission denied for schema public` (during `migrate`) | PostgreSQL 15+ only lets the database owner create tables in `public`. | `ALTER DATABASE scams OWNER TO scams_app;` or, connected to `scams`: `GRANT USAGE, CREATE ON SCHEMA public TO scams_app;` |
| `database "scams" does not exist` / `role "scams_app" does not exist` | Not created yet, or a typo in `POSTGRES_DB`/`POSTGRES_USER`. | Section 1.2. |
| `permission denied to create database` (during `manage.py test`) | The test runner needs `CREATEDB`. | `ALTER ROLE scams_app CREATEDB;` and allow the `postgres` and `test_scams` databases in `pg_hba.conf`, or run tests on SQLite. |
| `value too long for type character varying(N)` (during `loaddata`) | SQLite accepted a value longer than the field allows. | See the end of section 3. |
| `pg_dump: error: aborting because of server version mismatch` | Local `pg_dump` is older than the server. | Install newer client tools and set `PG_DUMP`. |
| `ImproperlyConfigured: POSTGRES_HOST is set ... but POSTGRES_DB ... missing` | Half-filled `.env`. | Fill in `POSTGRES_DB` and `POSTGRES_USER`, or comment out `POSTGRES_HOST` to use SQLite. |
