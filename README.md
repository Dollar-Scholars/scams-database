# scams-database
Developed by volunteers from the Economics discord server.


## Setup
```yaml
# April 10, 2026
# Instructions by Leslie D. @lespam for Economics Server Discord.
# Requires Git and Anaconda.


git clone https://github.com/Dollar-Scholars/scams-database.git

####################################
# create conda environment
####################################
# if you have the file
conda env create -f environment.yml
# else
conda create -n scams python Django

conda activate scams

##############################
# makemigrations and run bot
##############################
# In the folder where manage.py file is
# First time only
python manage.py migrate
python manage.py makemigrations
python manage.py migrate

# From now on
git pull

# Everytime the db is updated you will need to run
python manage.py makemigrations
python manage.py migrate

python manage.py run_bot

##############################
# push your results
##############################
git add .
git commit -m 'message'
git push
```
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
