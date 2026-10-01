# Deploying to scamdb.dollarscholars.org

The Scams DB runs on the same VM as the quiz, set up the same
way: a Docker container that only listens on `127.0.0.1`, with nginx in front.
The two sites don't share anything except nginx and the machine.

| | Quiz | Scams DB |
|---|---|---|
| Domain | quiz.dollarscholars.org | scamdb.dollarscholars.org |
| Container | (the quiz's container) | `scamdb-app` |
| Port (localhost only) | 8000 | 8001 |
| nginx site | `/etc/nginx/sites-enabled/quiz` | `/etc/nginx/sites-enabled/scamdb.dollarscholars.org` |
| Code | (the quiz's checkout) | `~/scams-database` |

The database is the `scams` database on the PostgreSQL VM, reached over Azure's
private network (no public port).

## One-time setup

### 1. DNS

Add a record for `scamdb` that is identical to the `quiz` record (same type,
target and proxy setting), wherever the dollarscholars.org DNS is managed.

### 2. PostgreSQL VM: database, role and access

If not done yet, create the role and database as in
[POSTGRES.md section 1.2](POSTGRES.md#12-create-a-role-and-a-database-least-privilege).
Use a password made of letters and digits only (`openssl rand -hex 24`):
Docker's `--env-file` passes quotes through literally.

The app connects from the quiz VM's private address (run `hostname -I` on the
quiz VM; the first address, e.g. `10.x.x.x` or `172.16.x.x`). Check whether
`pg_hba.conf` already allows it (the quiz's own entry may cover it):

```bash
sudo -u postgres psql -c 'SHOW hba_file;'
sudo grep -vE '^\s*(#|$)' /etc/postgresql/18/main/pg_hba.conf
```

If no line covers database `scams`, user `scams_app` from that address, add this one
at the end and reload (a reload does not interrupt existing connections):

```text
host    scams    scams_app    <quiz-vm-private-ip>/32    scram-sha-256
```

```bash
sudo systemctl reload postgresql
```

### 3. Quiz VM: get the code and create `.env`

```bash
cd ~
git clone https://github.com/Dollar-Scholars/scams-database.git
cd scams-database
cp .env.example .env
nano .env
```

Set these (no quotes around values):

```ini
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<output of: openssl rand -hex 50>
DJANGO_ALLOWED_HOSTS=scamdb.dollarscholars.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://scamdb.dollarscholars.org
DJANGO_SECURE_PROXY_SSL_HEADER=True

POSTGRES_HOST=<private IP of the PostgreSQL VM>
POSTGRES_PORT=5432
POSTGRES_DB=scams
POSTGRES_USER=scams_app
POSTGRES_PASSWORD=<the scams_app password>
POSTGRES_SSLMODE=prefer
```

Lock the file down: `chmod 600 .env`.

Check the connection before going further:

```bash
docker build -t scamdb-app:latest .
docker run --rm --env-file .env scamdb-app:latest python manage.py db_status
```

### 4. Start the app

```bash
bash deploy/deploy.sh
docker exec -it scamdb-app python manage.py createsuperuser
```

`deploy.sh` builds the image, runs migrations, (re)starts the container with
`--restart unless-stopped` (so it comes back after a reboot) and checks it answers.

### 5. nginx and HTTPS

```bash
sudo cp deploy/nginx/scamdb.dollarscholars.org /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/scamdb.dollarscholars.org /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Then get the certificate the same way the quiz did. With certbot:

```bash
sudo certbot --nginx -d scamdb.dollarscholars.org
```

Open https://scamdb.dollarscholars.org. Once HTTPS works you can also set
`DJANGO_SECURE_SSL_REDIRECT=True` in `.env` and run `bash deploy/deploy.sh` again.

## Updating

After changes are merged into `main`:

```bash
bash ~/scams-database/deploy/deploy.sh
```

## Useful commands

```bash
docker logs --tail 100 scamdb-app          # app log (one line per request)
docker exec -it scamdb-app python manage.py db_status
docker restart scamdb-app
docker ps                                  # both containers should be listed
```

The VM has 2 CPUs and about 4 GB of memory, which is plenty for both sites; the
Scams DB container uses roughly 150-250 MB. The VM has no swap, so adding a 2 GB
swap file is a cheap safety net:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
