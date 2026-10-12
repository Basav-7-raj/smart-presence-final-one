from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import RequestFactory, TestCase
from django.http import HttpResponse
from django.core.files.uploadedfile import SimpleUploadedFile
from tracker import views

from tracker.models import PersonProfile, PresenceRecord, UnknownEvent, SystemEvent, LocationSite
from tracker.face_engine import feature_templates_from_json


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

    def test_health_runs_inference_probe_instead_of_only_checking_file_presence(self):
        with patch("tracker.views.models_ready", return_value=True), \\
             patch("tracker.face_engine.get_models"), \\
             patch("tracker.face_engine.detect_faces", return_value=[]):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["models_ready"])
        self.assertTrue(response.json()["inference_ready"])
        self.assertTrue(response.json()["ready"])

    def test_health_reports_model_runtime_failure(self):
        with patch("tracker.views.models_ready", return_value=True), \\
             patch("tracker.face_engine.get_models", side_effect=RuntimeError("ONNX init failed")):
            response = self.client.get("/health/")
        self.assertFalse(response.json()["inference_ready"])
        self.assertFalse(response.json()["ready"])
        self.assertIn("ONNX init failed", response.json()["inference_error"])


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


class MultiPhotoRegistrationTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user(username="test-admin", password="test-password-123")
        self.client.force_login(self.user)

    def test_feature_parser_supports_legacy_and_multi_sample_profiles(self):
        self.assertEqual(feature_templates_from_json('[0.1, 0.2]'), [[0.1, 0.2]])
        self.assertEqual(feature_templates_from_json('[[0.1, 0.2], [0.3, 0.4]]'), [[0.1, 0.2], [0.3, 0.4]])

    def test_registration_saves_embeddings_from_multiple_photos(self):
        files = [
            SimpleUploadedFile("front.jpg", b"front-image", content_type="image/jpeg"),
            SimpleUploadedFile("angle.jpg", b"angle-image", content_type="image/jpeg"),
        ]
        with patch("tracker.views.cv2.imdecode", return_value=object()), \\
             patch("tracker.views.extract_best_feature", side_effect=[([0.1, 0.2], {}), ([0.3, 0.4], {})]):
            response = self.client.post("/register/", {
                "name": "Test Person",
                "student_id": "MULTI-001",
                "images": files,
            })
        self.assertEqual(response.status_code, 200, response.content.decode())
        self.assertEqual(response.json()["samples_saved"], 2)
        person = PersonProfile.objects.get(student_id="MULTI-001")
        self.assertEqual(feature_templates_from_json(person.encoding_json), [[0.1, 0.2], [0.3, 0.4]])



class LocationAwareSiteTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user(username="location-admin", password="test-password-123")
        self.client.force_login(self.user)

    def test_create_and_select_fixed_camera_site(self):
        response = self.client.post("/locations/save/", {
            "name": "Main Gate Camera",
            "address": "Main gate, campus",
            "latitude": "12.971599",
            "longitude": "77.594566",
            "select_site": "1",
        })
        self.assertEqual(response.status_code, 200, response.content.decode())
        site = LocationSite.objects.get(name="Main Gate Camera")
        self.assertEqual(str(site.latitude), "12.971599")
        data = self.client.get("/locations/data/").json()
        self.assertEqual(data["active_site_id"], site.id)
        self.assertTrue(data["sites"][0]["selected"])

    def test_reject_partial_coordinates(self):
        response = self.client.post("/locations/save/", {
            "name": "Address Only",
            "address": "Building 2",
            "latitude": "12.0",
            "longitude": "",
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LocationSite.objects.filter(name="Address Only").exists())

    def test_location_page_requires_admin_login(self):
        self.client.logout()
        response = self.client.get("/locations/")
        self.assertEqual(response.status_code, 302)
