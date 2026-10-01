# scams-database
Developed by volunteers from the Economics discord server.

A Django app where people report scams, with a dashboard, a list of reports and
a scam awareness page. It runs on SQLite with zero setup; PostgreSQL is optional.

## Setup
Requires Git and Python 3.10 to 3.14 (or Anaconda/Miniconda).

### 1. Get the code
```bash
git clone https://github.com/Dollar-Scholars/scams-database.git
cd scams-database
```

### 2. Create an environment (pick one)
**venv, Windows PowerShell**
```powershell
py -3.14 -m venv .venv      # any installed 3.10 to 3.14 works; py --list shows them
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
If `Activate.ps1` fails with "running scripts is disabled on this system", allow
local scripts for your user once, then activate again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Or skip activation and run the venv's Python directly, e.g.
`.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and
`.\.venv\Scripts\python.exe manage.py runserver`.

**venv, macOS/Linux**
```bash
python3 --version           # must be 3.10 to 3.14; if not, use e.g. python3.12 in the next line
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**conda**
```bash
conda env create -f environment.yml
conda activate scams
```

### 3. Configure
Copy the example settings. The defaults (debug mode, SQLite) work as-is for local development.
```powershell
Copy-Item .env.example .env     # macOS/Linux: cp .env.example .env
```
`.env` is git-ignored; never commit it. Every setting is explained in `.env.example`.

### 4. Create the database and run
```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```
Open http://127.0.0.1:8000/

### Everyday commands
```bash
git pull
python -m pip install -r requirements.txt   # when requirements.txt changed
python manage.py migrate                    # apply new migrations from others
python manage.py makemigrations             # only after YOU changed scams/models.py
python manage.py test scams                 # run the tests
python manage.py db_status                  # which database am I on? pending migrations?
python manage.py backup_db                  # back up the database into ./backups
```

### PostgreSQL (optional)
To use a PostgreSQL server (for example on a separate VM), set the `POSTGRES_*`
variables in `.env`. See **[docs/POSTGRES.md](docs/POSTGRES.md)** for server setup,
moving existing SQLite data, backups and troubleshooting.

### Production (scamdb.dollarscholars.org)
The live site runs in Docker next to the quiz. See **[docs/DEPLOY.md](docs/DEPLOY.md)**.

## How to contribute
### 1. Add Yourself as a Contributor
- Open this link: https://github.com/Dollar-Scholars/koala-bor-ed-with-us
- Add your name to the Contributors to get started and be added to the project
### 2. Set Up the Project
- Follow the setup instructions above
### 3. Create a Branch
- Use the naming convention:  
`your-name/short-task-description`
- Example: maymay/reports-view
### 4. Make Your Changes
- Test your code before committing
### 5. Commit Your Work
```bash
git add .
git commit -m "clear description of your change"
```
### 6. Push Your Branch
```bash
git push
```
### 7. Open a Pull Request
- Describe what you changed
