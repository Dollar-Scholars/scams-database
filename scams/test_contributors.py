from django.test import TestCase
from django.urls import reverse

from .contributors import CONTRIBUTORS


class ContributorsPageTest(TestCase):
    def test_lists_every_contributor_with_github_link(self):
        response = self.client.get(reverse('contributors'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'scams/base.html')
        for person in CONTRIBUTORS:
            self.assertContains(response, f'href="https://github.com/{person["github"]}"')
            self.assertContains(response, person['work'])

    def test_every_entry_has_github_and_work(self):
        for person in CONTRIBUTORS:
            self.assertTrue(person.get('github'))
            self.assertTrue(person.get('work'))

    def test_footer_links_to_contributors_on_every_page(self):
        link = f'href="{reverse("contributors")}"'
        for name in ('report_scam', 'dashboard', 'scam_list', 'thank_you', 'scam_awareness_page', 'contributors'):
            response = self.client.get(reverse(name))
            self.assertContains(response, link, msg_prefix=name)
