from rest_framework.test import APITestCase

from .models import Profile

PASSWORD = "not-a-common-password-123"


class AuthFlowTest(APITestCase):
    def test_register_me_login(self):
        r = self.client.post(
            "/api/auth/register/",
            {"email": "a@b.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertIn("access", r.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        r = self.client.get("/api/auth/me/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["email"], "a@b.com")

        r = self.client.post(
            "/api/auth/login/",
            {"username": "a@b.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

        r = self.client.post(
            "/api/auth/login/",
            {"username": "a@b.com", "password": "nope-1"},
            format="json",
        )
        self.assertEqual(r.status_code, 401)

    def test_register_rejects_duplicate_and_weak(self):
        for _ in range(2):
            r = self.client.post(
                "/api/auth/register/",
                {"email": "x@y.com", "password": PASSWORD},
                format="json",
            )
        self.assertEqual(r.status_code, 400)  # second attempt: duplicate email

        r = self.client.post(
            "/api/auth/register/",
            {"email": "z@y.com", "password": "1234"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)  # weak password hitting your validators

    def test_login_by_email_or_username_for_admin_style_user(self):
        Profile.objects.create_user(
            username="admin", email="boss@raahi.app", password="cli-password-99"
        )
        for ident in ("admin", "boss@raahi.app", "BOSS@raahi.app"):
            r = self.client.post(
                "/api/auth/login/",
                {"username": ident, "password": "cli-password-99"},
                format="json",
            )
            self.assertEqual(r.status_code, 200)

    def test_chat_requires_login(self):
        r = self.client.post(
            "/api/chat/", {"destination": "Agra", "message": "hi"}, format="json"
        )
        self.assertEqual(r.status_code, 401)

        token = self.client.post(
            "/api/auth/register/",
            {"email": "chat@x.com", "password": PASSWORD},
            format="json",
        ).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")
        r = self.client.post(
            "/api/chat/", {"destination": "Agra", "message": "hi"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("reply", r.data)

    def test_profile_update_and_avatar(self):
        import base64
        from tempfile import TemporaryDirectory

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings

        token = self.client.post(
            "/api/auth/register/",
            {"email": "pic@x.com", "password": PASSWORD},
            format="json",
        ).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")

        r = self.client.patch(
            "/api/auth/me/",
            {"first_name": "Ada", "bio": "Wanderer", "birth_date": "1994-05-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["first_name"], "Ada")
        self.assertEqual(r.data["birth_date"], "1994-05-01")

        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            r = self.client.patch(
                "/api/auth/me/",
                {
                    "profile_picture": SimpleUploadedFile(
                        "a.png", png, content_type="image/png"
                    )
                },
                format="multipart",
            )
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.data["profile_picture"].endswith(".png"))

            r = self.client.patch(
                "/api/auth/me/",
                {
                    "profile_picture": SimpleUploadedFile(
                        "a.txt", b"hi", content_type="text/plain"
                    )
                },
                format="multipart",
            )
            self.assertEqual(r.status_code, 400)  # not an image


class PlanApiTest(APITestCase):
    def auth(self, email):
        r = self.client.post(
            "/api/auth/register/",
            {"email": email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def login(self, email):
        r = self.client.post(
            "/api/auth/login/",
            {"username": email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def make_plan(self, **overrides):
        payload = {
            "title": "Rajasthan road trip",
            "destination": "Jaipur",
            "start_date": "2026-11-01",
            "end_date": "2026-11-06",
            "notes": "Palaces and chai.",
        }
        payload.update(overrides)
        return self.client.post("/api/plans/", payload, format="json")

    def test_plan_crud(self):
        self.auth("planner@x.com")
        r = self.make_plan()
        self.assertEqual(r.status_code, 201)
        plan_id = r.data["id"]
        self.assertEqual(r.data["status"], "wishlist")
        self.assertEqual(r.data["items"], [])

        r = self.client.get("/api/plans/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)

        r = self.client.patch(
            f"/api/plans/{plan_id}/",
            {"status": "planned", "notes": "Train booked."},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "planned")

        self.assertEqual(
            self.client.delete(f"/api/plans/{plan_id}/").status_code, 204
        )
        self.assertEqual(self.client.get("/api/plans/").data, [])

    def test_plan_validation(self):
        self.auth("dates@x.com")
        r = self.make_plan(end_date="2026-10-01")
        self.assertEqual(r.status_code, 400)
        self.assertIn("end_date", r.data)

        r = self.client.post("/api/plans/", {"destination": "Agra"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("title", r.data)

    def test_plan_owner_scoping(self):
        self.auth("owner@x.com")
        plan_id = self.make_plan().data["id"]

        self.auth("other@x.com")
        self.assertEqual(self.client.get("/api/plans/").data, [])
        self.assertEqual(self.client.get(f"/api/plans/{plan_id}/").status_code, 404)
        self.assertEqual(
            self.client.patch(
                f"/api/plans/{plan_id}/", {"title": "Mine now"}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"/api/plans/{plan_id}/").status_code, 404
        )

    def test_plan_items_crud_and_ownership(self):
        self.auth("stops@x.com")
        plan_id = self.make_plan().data["id"]

        r = self.client.post(
            "/api/plan-items/",
            {"plan": plan_id, "category": "food", "name": "Laxmi Mishthan"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        item_id = r.data["id"]

        r = self.client.get(f"/api/plans/{plan_id}/")
        self.assertEqual(len(r.data["items"]), 1)
        self.assertEqual(r.data["items"][0]["name"], "Laxmi Mishthan")

        r = self.client.patch(
            f"/api/plan-items/{item_id}/",
            {"time": "2026-11-02T10:30:00Z", "cost": "250.00"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["time"].startswith("2026-11-02"))

        self.auth("intruder@x.com")
        self.assertEqual(self.client.get("/api/plan-items/").data, [])
        r = self.client.post(
            "/api/plan-items/",
            {"plan": plan_id, "category": "place", "name": "Hawa Mahal"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)  # plan is not this user's

        self.login("stops@x.com")
        self.assertEqual(
            self.client.delete(f"/api/plan-items/{item_id}/").status_code, 204
        )
        self.assertEqual(
            len(self.client.get(f"/api/plans/{plan_id}/").data["items"]), 0
        )

    def test_plans_require_login(self):
        self.assertEqual(self.client.get("/api/plans/").status_code, 401)
        self.assertEqual(self.client.get("/api/plan-items/").status_code, 401)
