from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import RequestFactory, TestCase
from django.http import HttpResponse
from tracker import views

from tracker.models import PersonProfile, PresenceRecord, UnknownEvent, SystemEvent


class DashboardTests(TestCase):
    def test_dashboard_sets_csrf_cookie_for_browser_recognition(self):
        # Stub template rendering; exercise the actual ensure_csrf_cookie decorator.
        with patch("tracker.views.render", return_value=HttpResponse("ok")):
            response = views.dashboard(RequestFactory().get("/"))
        self.assertIn("csrftoken", response.cookies)

    def test_camera_requires_an_explicit_click_and_uses_controller_module(self):
        # Read the source template rather than using Client.get("/") here.
        # Django 4.2's template-render capture raises an internal Context.__copy__
        # error on Python 3.14; rendering itself is covered by the supported CI runtime.
        template_path = Path(settings.BASE_DIR) / "tracker" / "templates" / "tracker" / "dashboard.html"
        template = template_path.read_text(encoding="utf-8")
        self.assertIn("Start Camera", template)
        self.assertIn("camera_controller.js", template)
        self.assertNotIn("window.addEventListener('load',function(){console.log", template)


class HealthEndpointTests(TestCase):
    def test_health_reports_missing_models_without_claiming_ready(self):
        with patch("tracker.views.models_ready", return_value=False):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["models_ready"])
        self.assertFalse(response.json()["ready"])

    def test_health_checks_database(self):
        response = self.client.get("/health/")
        self.assertTrue(response.json()["database"])


class RecognitionEndpointTests(TestCase):
    def test_invalid_frame_returns_visible_client_error(self):
        response = self.client.post("/recognize/", data=b"not-an-image", content_type="image/jpeg")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")

    def test_method_other_than_post_is_rejected(self):
        response = self.client.get("/recognize/")
        self.assertEqual(response.status_code, 405)


class RegressionPreservationTests(TestCase):
    def test_registration_and_presence_models_remain_available(self):
        # These existing models are deliberately preserved: no schema change is needed.
        self.assertTrue(PersonProfile)
        self.assertTrue(PresenceRecord)
        self.assertTrue(UnknownEvent)
        self.assertTrue(SystemEvent)
