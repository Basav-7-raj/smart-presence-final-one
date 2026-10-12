from unittest.mock import patch

from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from tracker import face_engine
from tracker.models import PersonProfile, PresenceRecord, UnknownEvent, SystemEvent


class HealthEndpointTests(TestCase):
    def test_health_reports_missing_models_without_claiming_ready(self):
        with patch('tracker.views.models_ready', return_value=False):
            response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['models_ready'])
        self.assertFalse(response.json()['ready'])

    def test_health_checks_database(self):
        response = self.client.get('/health/')
        self.assertTrue(response.json()['database'])


class RecognitionEndpointTests(TestCase):
    def test_invalid_frame_returns_visible_client_error(self):
        response = self.client.post('/recognize/', data=b'not-an-image', content_type='image/jpeg')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

    def test_method_other_than_post_is_rejected(self):
        response = self.client.get('/recognize/')
        self.assertEqual(response.status_code, 405)


class RegressionPreservationTests(TestCase):
    def test_registration_and_presence_models_remain_available(self):
        self.assertTrue(PersonProfile)
        self.assertTrue(PresenceRecord)
        self.assertTrue(UnknownEvent)
        self.assertTrue(SystemEvent)
