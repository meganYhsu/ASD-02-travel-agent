import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import coordinator
from app import app


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        for name in ("HISTORY_PATH", "AUDIT_PATH", "HUMAN_REVIEW_PATH"):
            patcher = patch.object(coordinator, name, Path(self.directory.name) / f"{name}.jsonl")
            patcher.start()
            self.addCleanup(patcher.stop)
        self.agents = {}
        for name in ("plan_workflow", "generate_output", "review_output"):
            patcher = patch.object(coordinator, name, return_value={"status": "success"})
            self.agents[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def test_services_receive_their_context_and_persist_reviews(self):
        for service, context in (
            ("traveller", {"profile": {"traveller_id": 3, "preferences": ["walking"]}}),
            ("booking", {"bookings": [{"booking_id": 12, "status": "confirmed"}]}),
            ("budget", {"budget": 1000, "expenses": [{"cost": 200}]}),
            ("itinerary", {"itinerary": {"itinerary_id": 9, "destination": "Paris"}}),
            ("documents", {"documents": [{"type": "passport", "expiry": "2028-01-01"}]}),
        ):
            with self.subTest(service=service):
                response = self.client.post("/workflow", json={
                    "service": service, "task": "summarise", "user_request": "Summarise my records",
                    "context": context,
                })
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                for agent in self.agents.values():
                    payload = json.loads(agent.call_args.args[0])
                    self.assertEqual(payload["context"], context)
                    self.assertEqual(payload["service"], service)
                workflow_id = result["workflow_id"]
                saved = self.client.get(f"/workflow/{workflow_id}").get_json()
                self.assertEqual(saved["context"], context)
                self.assertEqual(saved["task"], "summarise")
                review = self.client.post(f"/workflow/{workflow_id}/review", json={
                    "decision": "Accept", "reason": "Verified against the supplied source records.",
                })
                self.assertEqual(review.status_code, 200)
                saved = self.client.get(f"/workflow/{workflow_id}").get_json()
                self.assertEqual(saved["human_decision"]["service"], service)
                self.assertEqual(saved["human_decision"]["status"], "recorded")
        audit = coordinator.read_jsonl(coordinator.AUDIT_PATH)
        self.assertEqual(len(audit), 5)
        self.assertEqual(audit[-1]["service"], "documents")

    def test_legacy_itinerary_is_compacted_and_keeps_response_fields(self):
        context = {
            "itinerary": {"itinerary_id": 86, "destination": "Zambia", "internal_field": "excluded"},
            "activities": [{"day_no": 1, "note": "Sunset cruise"}],
        }
        response = self.client.post("/workflow", json={
            "user_request": "Summarise itinerary 86", "itinerary_context": context,
        })
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["itinerary_id"], 86)
        self.assertEqual(result["itinerary_context"], context)
        self.assertEqual(result["service"], "itinerary")
        payload = json.loads(self.agents["generate_output"].call_args.args[0])
        self.assertNotIn("internal_field", payload["context"]["itinerary"])
        columns = payload["context"]["activity_columns"]
        self.assertEqual(payload["context"]["activities"][0][columns.index("note")], "Sunset cruise")

    def test_invalid_requests_do_not_call_agents(self):
        invalid_bodies = [
            [], {}, {"user_request": 1}, {"user_request": " "},
            {"service": "booking", "task": "summarise"},
            {"service": "", "task": "summarise", "context": {}},
            {"service": "booking", "task": [], "context": {}},
            {"service": "booking", "task": "summarise", "context": []},
            {"service": "booking", "task": "summarise", "context": {}, "itinerary_context": None},
            {"itinerary_context": {"itinerary": {"itinerary_id": True}, "activities": []}},
            {"itinerary_context": {"itinerary": {"itinerary_id": 1}, "activities": [None]}},
        ]
        for body in invalid_bodies:
            with self.subTest(body=body):
                if isinstance(body, dict):
                    body = {"user_request": "Summarise", **body}
                    if body == {"user_request": "Summarise"}:
                        body = {}
                self.assertEqual(self.client.post("/workflow", json=body).status_code, 400)
        self.agents["generate_output"].assert_not_called()

    def test_request_only_and_empty_context_remain_supported(self):
        for body in (
            {"user_request": "What data is missing?"},
            {"user_request": "What data is missing?", "service": "custom", "task": "check", "context": {}},
        ):
            self.assertEqual(self.client.post("/workflow", json=body).status_code, 200)

    def test_worker_failure_requires_review(self):
        self.agents["generate_output"].return_value = {"status": "error", "error": "Model unavailable"}
        response = self.client.post("/workflow", json={
            "user_request": "Summarise", "service": "booking", "task": "summarise", "context": {},
        })
        self.assertEqual(response.get_json()["status"], "partial_failure")
        self.assertTrue(response.get_json()["human_decision"]["required"])


if __name__ == "__main__":
    unittest.main()
