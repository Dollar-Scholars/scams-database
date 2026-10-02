"""People who built Scam Reports, shown on /contributors/.

To add yourself: append an entry below (GitHub username, what you worked on)
and open a pull request. "name" is optional; leave it out to show only your
GitHub username. "work" is shown in the page's language, so it is wrapped in _() to be
picked up for translation.
"""
from django.utils.translation import gettext_lazy as _

CONTRIBUTORS = [
    {
        'github': 'ngomayling',
        'work': _('Started the original scam database, built the dashboard and its charts, '
                  'and wrote the contributor guide.'),
    },
    {
        'github': 'lespam',
        'work': _('Set up the project and its data model, deployment and migrations, '
                  'and added more currencies.'),
    },
    {
        'github': 'lockstepsim',
        'work': _('Designed and built the scam report form.'),
    },
    {
        'github': 'grezziam',
        'work': _('Created the scam awareness pages.'),
    },
    {
        'github': 'keplarrs',
        'work': _('Added detection of duplicate reports, with tests.'),
    },
    {
        'github': 'jdickinson202',
        'work': _('Moved the site to PostgreSQL, gave it the Dollar Scholars look, upgraded '
                  'Django and launched scamdb.dollarscholars.org.'),
    },
]
