from __future__ import annotations

import asyncio
import json
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lot.main import create_app


@dataclass
class AsgiResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))


async def make_request(app, method: str, path: str, payload: dict[str, Any] | None = None) -> AsgiResponse:
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    headers = [(b"host", b"testserver")]
    if body:
        headers.append((b"content-type", b"application/json"))
        headers.append((b"content-length", str(len(body)).encode("ascii")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    request_sent = False
    response_status = 500
    response_headers: dict[str, str] = {}
    response_body = bytearray()

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal response_status, response_headers
        if message["type"] == "http.response.start":
            response_status = int(message["status"])
            response_headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    await app(scope, receive, send)
    return AsgiResponse(status_code=response_status, headers=response_headers, body=bytes(response_body))


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> AsgiResponse:
        return asyncio.run(make_request(self.app, method, path, payload))

    def assert_request_id(self, response: AsgiResponse) -> str:
        payload = response.json()
        request_id = payload["request_id"]
        self.assertTrue(request_id.startswith("req-"))
        self.assertEqual(response.headers.get("x-request-id"), request_id)
        return request_id

    def test_capabilities_returns_success_envelope(self) -> None:
        response = self.request("GET", "/v1/capabilities")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload)
        self.assertEqual(payload["data"]["api_version"], "v1")
        self.assertIn("device_sim", payload["data"]["modes"])
        self.assert_request_id(response)

    def test_create_session_returns_initial_state_snapshot(self) -> None:
        response = self.request(
            "POST",
            "/v1/sessions",
            {"board_profile": "profiles/example_stm32f4.yaml", "seed": 7},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("session", payload["data"])
        self.assertIn("state", payload["data"])
        self.assertEqual(payload["data"]["session"]["seed"], 7)
        self.assertEqual(payload["data"]["state"]["board"]["board"], "example_stm32f4")
        self.assert_request_id(response)

    def test_validation_errors_use_stable_envelope(self) -> None:
        response = self.request("POST", "/v1/sessions", {"seed": 1})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["error_code"], "INVALID_REQUEST")
        self.assertIn("errors", payload["error"]["details"])
        self.assert_request_id(response)

    def test_domain_errors_keep_specific_error_code(self) -> None:
        response = self.request(
            "POST",
            "/v1/sessions",
            {"board_profile": "profiles/example_stm32f4.yaml", "mode": "firmware_sim"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["error_code"], "MODE_NOT_SUPPORTED")
        self.assert_request_id(response)

    def test_missing_session_maps_to_not_found(self) -> None:
        response = self.request("GET", "/v1/sessions/sess-missing/state")

        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["error_code"], "SESSION_NOT_FOUND")
        self.assert_request_id(response)

    def test_io_path_segments_are_validated(self) -> None:
        session_response = self.request(
            "POST",
            "/v1/sessions",
            {"board_profile": "profiles/example_stm32f4.yaml"},
        )
        session_id = session_response.json()["data"]["session"]["session_id"]

        response = self.request(
            "POST",
            f"/v1/sessions/{session_id}/io/GPIO:set",
            {"params": {}},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["error_code"], "INVALID_REQUEST")
        self.assert_request_id(response)

    def test_scenario_requires_exactly_one_source(self) -> None:
        session_response = self.request(
            "POST",
            "/v1/sessions",
            {"board_profile": "profiles/example_stm32f4.yaml"},
        )
        session_id = session_response.json()["data"]["session"]["session_id"]

        response = self.request(
            "POST",
            f"/v1/sessions/{session_id}/scenario:run",
            {"scenario_path": "scenarios/example_i2c_stuck.yaml", "scenario_text": "version: v1alpha1"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["error_code"], "INVALID_REQUEST")
        self.assert_request_id(response)


if __name__ == "__main__":
    unittest.main()
