import json
import urllib.error
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from . import llm, tools
from .llm import LLMError, LLMNotConfigured
from .models import Plan, Profile, ToolCache

PASSWORD = "not-a-common-password-123"

GENERATED = {
    "title": "Jaipur in two days",
    "destination": "Jaipur",
    "summary": "Old city mornings and forts at dawn.",
    "days": [
        {
            "title": "Arrive and wander",
            "items": [
                {
                    "time": "09:00",
                    "category": "place",
                    "name": "Hawa Mahal",
                    "notes": "Go early.",
                    "cost": 200,
                },
                {
                    "time": "13:00",
                    "category": "food",
                    "name": "Laxmi Mishthan",
                    "notes": "",
                    "cost": None,
                },
            ],
        },
        {
            "title": "Forts",
            "items": [
                {
                    "time": "08:30",
                    "category": "place",
                    "name": "Amber Fort",
                    "notes": "",
                    "cost": 500,
                },
                {
                    "time": "later",
                    "category": "made-up",
                    "name": "Bazaar",
                    "notes": "",
                    "cost": "free",
                },
            ],
        },
    ],
}


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

    def test_chat_requires_login_and_replies(self):
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

        with patch("api.views.chat_reply", return_value="Go at sunrise.") as reply:
            r = self.client.post(
                "/api/chat/",
                {"destination": "Agra", "message": "What should I see?"},
                format="json",
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["reply"], "Go at sunrise.")
        reply.assert_called_once_with("What should I see?", "Agra")

        r = self.client.post("/api/chat/", {"message": ""}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_chat_handles_missing_config_and_provider_errors(self):
        token = self.client.post(
            "/api/auth/register/",
            {"email": "chat-errors@x.com", "password": PASSWORD},
            format="json",
        ).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")

        with patch("api.views.chat_reply", side_effect=LLMNotConfigured):
            r = self.client.post(
                "/api/chat/", {"destination": "Agra", "message": "hi"}, format="json"
            )
        self.assertEqual(r.status_code, 503)
        self.assertIn("detail", r.data)

        with patch("api.views.chat_reply", side_effect=LLMError("boom")):
            r = self.client.post(
                "/api/chat/", {"destination": "Agra", "message": "hi"}, format="json"
            )
        self.assertEqual(r.status_code, 502)
        self.assertIn("detail", r.data)

    def test_profile_update_and_avatar(self):
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

        def photo(color, name):
            buffer = BytesIO()
            Image.new("RGB", (2, 2), color).save(buffer, "PNG")
            return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            r = self.client.patch(
                "/api/auth/me/",
                {"profile_picture": photo((220, 40, 40), "one.png")},
                format="multipart",
            )
            self.assertEqual(r.status_code, 200)
            first_url = r.data["profile_picture"]
            first_path = Path(tmp) / first_url.removeprefix("/media/")
            self.assertTrue(first_path.exists())

            r = self.client.patch(
                "/api/auth/me/",
                {"profile_picture": photo((20, 120, 220), "two.png")},
                format="multipart",
            )
            self.assertEqual(r.status_code, 200)
            second_url = r.data["profile_picture"]
            second_path = Path(tmp) / second_url.removeprefix("/media/")
            self.assertNotEqual(second_url, first_url)
            self.assertTrue(second_path.exists())
            self.assertFalse(first_path.exists())  # replaced file is removed

            r = self.client.patch(
                "/api/auth/me/",
                {
                    "profile_picture": SimpleUploadedFile(
                        "fake.png", b"not really an image", content_type="image/png"
                    )
                },
                format="multipart",
            )
            self.assertEqual(r.status_code, 400)
            r = self.client.get("/api/auth/me/")
            self.assertEqual(r.data["profile_picture"], second_url)

            r = self.client.patch(
                "/api/auth/me/",
                {
                    "profile_picture": SimpleUploadedFile(
                        "big.png",
                        b"x" * (2 * 1024 * 1024 + 1),
                        content_type="image/png",
                    )
                },
                format="multipart",
            )
            self.assertEqual(r.status_code, 400)

            r = self.client.patch(
                "/api/auth/me/", {"remove_profile_picture": True}, format="json"
            )
            self.assertEqual(r.status_code, 200)
            self.assertIsNone(r.data["profile_picture"])
            self.assertFalse(second_path.exists())

            # Removing again is a harmless no-op.
            r = self.client.patch(
                "/api/auth/me/", {"remove_profile_picture": "true"}, format="json"
            )
            self.assertEqual(r.status_code, 200)
            self.assertIsNone(r.data["profile_picture"])

    def test_invalid_avatar_rolls_back_other_profile_edits(self):
        token = self.client.post(
            "/api/auth/register/",
            {"email": "rollback@x.com", "password": PASSWORD},
            format="json",
        ).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")

        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            r = self.client.patch(
                "/api/auth/me/",
                {
                    "first_name": "Should not stick",
                    "bio": "Nor this",
                    "profile_picture": SimpleUploadedFile(
                        "fake.png", b"not really an image", content_type="image/png"
                    ),
                },
                format="multipart",
            )
            self.assertEqual(r.status_code, 400)
            self.assertFalse(list(Path(tmp).rglob("*")))

        r = self.client.get("/api/auth/me/")
        self.assertEqual(r.data["first_name"], "")
        self.assertEqual(r.data["bio"], "")
        self.assertIsNone(r.data["profile_picture"])


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

    @patch("api.views.generate_itinerary", return_value=GENERATED)
    def test_generate_creates_plan_with_day_by_day_items(self, generate):
        self.auth("ai@x.com")
        r = self.client.post(
            "/api/plans/generate/",
            {
                "prompt": "Two days in Jaipur from Delhi, street food and forts.",
                "start_date": "2026-11-01",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["title"], "Jaipur in two days")
        self.assertEqual(r.data["destination"], "Jaipur")
        self.assertEqual(r.data["status"], "planned")
        self.assertEqual(r.data["start_date"], "2026-11-01")
        self.assertEqual(r.data["end_date"], "2026-11-02")
        self.assertEqual(r.data["notes"], "Old city mornings and forts at dawn.")
        self.assertEqual(len(r.data["items"]), 4)

        first, second, third, fourth = r.data["items"]
        self.assertEqual(first["category"], "place")
        self.assertEqual(first["details"]["day"], 1)
        self.assertEqual(first["details"]["time"], "09:00")
        self.assertTrue(first["time"].startswith("2026-11-01T09:00"))
        self.assertEqual(second["details"]["day"], 1)
        self.assertEqual(third["details"]["day"], 2)
        self.assertTrue(third["time"].startswith("2026-11-02T08:30"))
        # Unparseable time/cost and unknown category degrade gracefully.
        self.assertIsNone(fourth["time"])
        self.assertIsNone(fourth["cost"])
        self.assertEqual(fourth["category"], "other")

        generate.assert_called_once_with(
            "Two days in Jaipur from Delhi, street food and forts.", "2026-11-01"
        )
        self.assertEqual(Plan.objects.filter(user__email="ai@x.com").count(), 1)

    @patch("api.views.generate_itinerary")
    def test_generate_validates_input_and_requires_login(self, generate):
        r = self.client.post("/api/plans/generate/", {"prompt": "Goa"}, format="json")
        self.assertEqual(r.status_code, 401)

        self.auth("ai-input@x.com")
        r = self.client.post("/api/plans/generate/", {"prompt": " "}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("prompt", r.data)

        r = self.client.post(
            "/api/plans/generate/",
            {"prompt": "Goa", "start_date": "next friday"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("start_date", r.data)
        generate.assert_not_called()

    @patch("api.views.generate_itinerary", return_value={"days": []})
    def test_generate_rejects_empty_itinerary(self, _generate):
        self.auth("ai-empty@x.com")
        r = self.client.post(
            "/api/plans/generate/", {"prompt": "Goa for a week"}, format="json"
        )
        self.assertEqual(r.status_code, 502)
        self.assertIn("detail", r.data)
        self.assertEqual(Plan.objects.count(), 0)

    def test_generate_handles_missing_config_and_provider_errors(self):
        self.auth("ai-errors@x.com")

        with patch("api.views.generate_itinerary", side_effect=LLMNotConfigured):
            r = self.client.post(
                "/api/plans/generate/", {"prompt": "Goa"}, format="json"
            )
        self.assertEqual(r.status_code, 503)

        with patch("api.views.generate_itinerary", side_effect=LLMError("boom")):
            r = self.client.post(
                "/api/plans/generate/", {"prompt": "Goa"}, format="json"
            )
        self.assertEqual(r.status_code, 502)
        self.assertEqual(Plan.objects.count(), 0)

    def test_plans_require_login(self):
        self.assertEqual(self.client.get("/api/plans/").status_code, 401)
        self.assertEqual(self.client.get("/api/plan-items/").status_code, 401)


class LLMClientTest(SimpleTestCase):
    @patch.dict(
        "os.environ",
        {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://llm.test/v1",
            "LLM_MODEL": "test-model",
        },
    )
    @patch("api.llm.urllib.request.urlopen")
    def test_chat_reply_sends_openai_payload(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = (
            b'{"choices":[{"message":{"content":" Visit at dawn. "}}]}'
        )

        reply = llm.chat_reply("What should I see?", "Jaipur")
        self.assertEqual(reply, "Visit at dawn.")

        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://llm.test/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer test-key")
        body = json.loads(req.data)
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(
            body["messages"][1], {"role": "user", "content": "What should I see?"}
        )
        self.assertIn("Jaipur", body["messages"][0]["content"])
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 20)

    @patch.dict("os.environ", {"LLM_MODEL": ""})
    def test_missing_model_raises_not_configured(self):
        with self.assertRaises(llm.LLMNotConfigured):
            llm.chat_reply("hi")

    @patch.dict("os.environ", {"LLM_MODEL": "test-model", "LLM_API_KEY": "k"})
    @patch("api.llm.urllib.request.urlopen", side_effect=urllib.error.URLError("down"))
    def test_unreachable_provider_raises_llm_error(self, _urlopen):
        with self.assertRaises(llm.LLMError):
            llm.chat_reply("hi")

    @patch.dict("os.environ", {"LLM_MODEL": "test-model"})
    @patch("api.llm.urllib.request.urlopen")
    def test_empty_reply_raises_llm_error(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = (
            b'{"choices":[{"message":{"content":"  "}}]}'
        )
        with self.assertRaises(llm.LLMError):
            llm.chat_reply("hi")

    @patch.dict("os.environ", {"LLM_MODEL": "test-model"})
    @patch("api.llm.execute_tool", return_value={"location": "Jaipur", "temp": 31})
    @patch("api.llm.urllib.request.urlopen")
    def test_chat_runs_tool_calls_before_answering(self, urlopen, execute):
        first = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location":"Jaipur"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        second = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "It is 31°C in Jaipur.",
                    }
                }
            ]
        }
        urlopen.return_value.__enter__.return_value.read.side_effect = [
            json.dumps(first).encode(),
            json.dumps(second).encode(),
        ]

        reply = llm.chat_reply("What is the weather in Jaipur?")
        self.assertEqual(reply, "It is 31°C in Jaipur.")
        execute.assert_called_once_with("get_weather", {"location": "Jaipur"})
        self.assertEqual(urlopen.call_count, 2)

        first_body = json.loads(urlopen.call_args_list[0].args[0].data)
        self.assertEqual(
            [tool["function"]["name"] for tool in first_body["tools"]],
            ["get_weather", "search_web", "get_wikipedia"],
        )
        second_body = json.loads(urlopen.call_args_list[1].args[0].data)
        tool_message = second_body["messages"][-1]
        self.assertEqual(tool_message["role"], "tool")
        self.assertEqual(tool_message["tool_call_id"], "call_1")
        self.assertIn("Jaipur", tool_message["content"])

    @patch.dict("os.environ", {"LLM_MODEL": "test-model"})
    @patch("api.llm.execute_tool", return_value={"ok": True})
    @patch("api.llm.urllib.request.urlopen")
    def test_tool_limit_forces_final_answer(self, urlopen, execute):
        responses = []
        for i in range(3):
            responses.append(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": f"call_{i}",
                                        "type": "function",
                                        "function": {
                                            "name": "get_weather",
                                            "arguments": json.dumps(
                                                {"location": f"City {i}"}
                                            ),
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            )
        responses.append(
            {
                "choices": [
                    {"message": {"content": "Final answer without more tools."}}
                ]
            }
        )
        urlopen.return_value.__enter__.return_value.read.side_effect = [
            json.dumps(response).encode() for response in responses
        ]

        reply = llm.chat_reply("Plan around the weather.")
        self.assertEqual(reply, "Final answer without more tools.")
        self.assertEqual(urlopen.call_count, 4)
        self.assertEqual(execute.call_count, 3)

        final_body = json.loads(urlopen.call_args_list[3].args[0].data)
        self.assertNotIn("tools", final_body)
        self.assertNotIn("tool_choice", final_body)

    @patch.dict("os.environ", {"LLM_MODEL": "test-model"})
    @patch("api.llm.execute_tool", return_value={"ok": True})
    @patch("api.llm.urllib.request.urlopen")
    def test_duplicate_tool_calls_run_once(self, urlopen, execute):
        call = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location":"Jaipur"}'},
        }
        first = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [call, {**call, "id": "call_2"}],
                    }
                }
            ]
        }
        second = {"choices": [{"message": {"content": "Done."}}]}
        urlopen.return_value.__enter__.return_value.read.side_effect = [
            json.dumps(first).encode(),
            json.dumps(second).encode(),
        ]

        self.assertEqual(llm.chat_reply("Weather?"), "Done.")
        execute.assert_called_once_with("get_weather", {"location": "Jaipur"})

        body = json.loads(urlopen.call_args_list[1].args[0].data)
        tool_messages = [m for m in body["messages"] if m["role"] == "tool"]
        self.assertEqual(len(tool_messages), 2)
        self.assertIn("duplicate", tool_messages[1]["content"])

    @patch.dict("os.environ", {"LLM_MODEL": "test-model"})
    @patch("api.llm.execute_tool", return_value={"ok": True})
    @patch("api.llm.urllib.request.urlopen")
    def test_tool_limit_keeps_content_from_a_stray_call(self, urlopen, execute):
        responses = []
        for i in range(3):
            responses.append(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": f"call_{i}",
                                        "type": "function",
                                        "function": {
                                            "name": "get_weather",
                                            "arguments": json.dumps(
                                                {"location": f"City {i}"}
                                            ),
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            )
        responses.append(
            {
                "choices": [
                    {
                        "message": {
                            "content": "Answer with what I have.",
                            "tool_calls": [
                                {
                                    "id": "call_4",
                                    "type": "function",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"location":"Elsewhere"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        )
        urlopen.return_value.__enter__.return_value.read.side_effect = [
            json.dumps(response).encode() for response in responses
        ]

        self.assertEqual(
            llm.chat_reply("Anything?"), "Answer with what I have."
        )
        self.assertEqual(execute.call_count, 3)
        final_body = json.loads(urlopen.call_args_list[3].args[0].data)
        self.assertNotIn("tools", final_body)

    @patch.dict("os.environ", {"LLM_MODEL": "test-model"})
    @patch("api.llm.urllib.request.urlopen")
    def test_generate_itinerary_asks_for_json(self, urlopen):
        content = '```json\n{"days":[{"items":[{"name":"Hawa Mahal"}]}]}\n```'
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": content}}]}
        ).encode()

        data = llm.generate_itinerary("Two days in Jaipur", "2026-11-01")
        self.assertEqual(data["days"][0]["items"][0]["name"], "Hawa Mahal")

        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertIn("Two days in Jaipur", body["messages"][1]["content"])
        self.assertIn("2026-11-01", body["messages"][1]["content"])
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 90)

    @patch.dict("os.environ", {"LLM_MODEL": "test-model"})
    @patch("api.llm.urllib.request.urlopen")
    def test_generate_itinerary_rejects_non_json(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "Sorry, no plan today."}}]}
        ).encode()
        with self.assertRaises(llm.LLMError):
            llm.generate_itinerary("Goa")


class DuckDuckGoParserTest(SimpleTestCase):
    def test_extracts_titles_urls_and_snippets(self):
        parser = tools._DuckDuckGoParser()
        parser.feed(
            """
            <div class="result">
              <a class="result__a"
                 href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Ffort&amp;rut=x">
                Amber <b>Fort</b> timings
              </a>
              <a class="result__snippet" href="#">Open <b>8am</b> to 6pm.</a>
            </div>
            """
        )
        self.assertEqual(
            parser.titles, [("Amber Fort timings", "https://example.com/fort")]
        )
        self.assertEqual(parser.snippets, ["Open 8am to 6pm."])


class ToolTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("api.tools._get_json")
    def test_weather_shapes_current_and_forecast(self, get_json):
        get_json.side_effect = [
            {
                "results": [
                    {
                        "name": "Jaipur",
                        "admin1": "Rajasthan",
                        "country": "India",
                        "latitude": 26.9,
                        "longitude": 75.8,
                    }
                ]
            },
            {
                "current": {
                    "temperature_2m": 31.2,
                    "apparent_temperature": 33,
                    "relative_humidity_2m": 40,
                    "wind_speed_10m": 8,
                    "weather_code": 0,
                },
                "daily": {
                    "time": ["2026-11-01", "2026-11-02"],
                    "weather_code": [0, 61],
                    "temperature_2m_max": [31, 28],
                    "temperature_2m_min": [18, 17],
                    "precipitation_probability_max": [0, 60],
                },
            },
        ]

        data = tools._weather({"location": "Jaipur"})
        self.assertEqual(data["location"], "Jaipur, Rajasthan, India")
        self.assertEqual(data["current"]["condition"], "Clear sky")
        self.assertEqual(data["daily"][0]["max_c"], 31)
        self.assertEqual(data["daily"][1]["condition"], "Slight rain")
        self.assertEqual(data["daily"][1]["rain_chance"], 60)

    @patch("api.tools._get_json")
    def test_wikipedia_returns_summary(self, get_json):
        get_json.side_effect = [
            {"query": {"search": [{"title": "Amber Fort"}]}},
            {
                "title": "Amber Fort",
                "extract": "A fort in Amer, Rajasthan.",
                "description": "Fort in Rajasthan",
                "content_urls": {
                    "desktop": {"page": "https://en.wikipedia.org/wiki/Amber_Fort"}
                },
            },
        ]

        data = tools._wikipedia({"topic": "Amber Fort history"})
        self.assertEqual(data["title"], "Amber Fort")
        self.assertEqual(data["summary"], "A fort in Amer, Rajasthan.")
        self.assertIn("Amber_Fort", data["url"])

    def test_execute_tool_caches_results(self):
        handler = Mock(return_value={"location": "Jaipur", "temp": 31})
        with patch.dict(tools.HANDLERS, {"get_weather": handler}):
            first = tools.execute_tool("get_weather", {"location": "Jaipur"})
            second = tools.execute_tool("get_weather", {"location": " Jaipur "})

        self.assertEqual(first, second)
        handler.assert_called_once()
        self.assertEqual(ToolCache.objects.count(), 1)
        self.assertEqual(ToolCache.objects.get().query, "jaipur")

    def test_fresh_db_entry_refills_the_memory_cache(self):
        handler = Mock(return_value={"location": "Jaipur", "temp": 31})
        with patch.dict(tools.HANDLERS, {"get_weather": handler}):
            first = tools.execute_tool("get_weather", {"location": "Jaipur"})
            ToolCache.objects.all().delete()  # simulate a restart or DB cleanup
            second = tools.execute_tool("get_weather", {"location": "Jaipur"})

        self.assertEqual(first, second)
        handler.assert_called_once()

    def test_expired_db_entry_is_refetched(self):
        ToolCache.objects.create(
            tool="get_weather",
            query="jaipur",
            data={"location": "Jaipur", "temp": 18},
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        handler = Mock(return_value={"location": "Jaipur", "temp": 31})
        with patch.dict(tools.HANDLERS, {"get_weather": handler}):
            data = tools.execute_tool("get_weather", {"location": "Jaipur"})

        self.assertEqual(data["temp"], 31)
        handler.assert_called_once()
        self.assertGreater(ToolCache.objects.get().expires_at, timezone.now())

    def test_cache_outage_does_not_break_the_tool(self):
        handler = Mock(return_value={"location": "Jaipur", "temp": 31})
        with (
            patch.dict(tools.HANDLERS, {"get_weather": handler}),
            patch("api.tools.cache.get", side_effect=RuntimeError("redis down")),
            patch("api.tools.cache.set", side_effect=RuntimeError("redis down")),
        ):
            data = tools.execute_tool("get_weather", {"location": "Jaipur"})

        self.assertEqual(data["temp"], 31)
        handler.assert_called_once()

    def test_unknown_tool_and_missing_input(self):
        self.assertEqual(
            tools.execute_tool("nope", {}), {"error": "unknown tool: nope"}
        )
        self.assertIn("error", tools.execute_tool("get_weather", {}))
        self.assertEqual(ToolCache.objects.count(), 0)

    def test_empty_search_results_are_not_cached(self):
        handler = Mock(
            return_value={"query": "nowhere", "results": [], "source": "DuckDuckGo"}
        )
        with patch.dict(tools.HANDLERS, {"search_web": handler}):
            data = tools.execute_tool("search_web", {"query": "nowhere"})
        self.assertEqual(data["results"], [])
        self.assertEqual(ToolCache.objects.count(), 0)
