from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Scam


class ScamAdminTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'x')
        self.client.force_login(user)
        Scam.objects.create(title='Bravo parcel', description='A long enough description.',
                            reporter_email='a@example.com', scam_type='financial', status='pending')
        Scam.objects.create(title='Alpha refund', description='Another long description.',
                            reporter_email='b@example.com', scam_type='identity', status='approved')
        self.url = reverse('admin:scams_scam_changelist')

    def test_changelist_shows_real_columns(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for column in ('column-title', 'column-scam_type', 'column-status', 'column-created_at'):
            self.assertContains(response, column)

    def test_sorting_by_title(self):
        # list_display index 1 is "title"
        response = self.client.get(self.url, {'o': '1'})
        titles = [scam.title for scam in response.context['cl'].result_list]
        self.assertEqual(titles, ['Alpha refund', 'Bravo parcel'])

    def test_search_and_status_filter(self):
        response = self.client.get(self.url, {'q': 'parcel'})
        self.assertEqual([s.title for s in response.context['cl'].result_list], ['Bravo parcel'])
        response = self.client.get(self.url, {'status': 'approved'})
        self.assertEqual([s.title for s in response.context['cl'].result_list], ['Alpha refund'])
