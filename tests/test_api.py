"""Demo API (plan Phase 8, docs/api-contract.md), exercised over real HTTP."""

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from api.app import make_server
from engine.layouts import QUALITY_WEIGHTS
from engine.resize import resize


ROOT = Path(__file__).resolve().parents[1]


def _sample(name):
    with (ROOT / "input" / name).open(encoding="utf-8") as handle:
        return json.load(handle)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path):
        try:
            with urllib.request.urlopen(self.base + path) as response:
                return response.status, response.headers["Content-Type"], response.read()
        except urllib.error.HTTPError as error:
            with error:
                return error.code, error.headers["Content-Type"], error.read()

    def _post(self, path, payload, raw=None):
        data = raw if raw is not None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base + path, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_health(self):
        status, _type, body = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_resize_returns_exactly_what_the_engine_returns(self):
        for name in ("chameleon_sample_level1_warmup.json", "chameleon_sample_level3_advanced.json"):
            task = _sample(name)
            with self.subTest(sample=name):
                status, body = self._post("/api/resize", {
                    "source": task["source"], "target_canvas": task["target_canvas"],
                })
                self.assertEqual(status, 200)
                self.assertEqual(body["design"], resize(task["source"], task["target_canvas"]))

    def test_debug_lists_every_candidate_with_the_full_breakdown(self):
        task = _sample("chameleon_sample_level2_core.json")
        status, body = self._post("/api/resize", {
            "source": task["source"], "target_canvas": {"width": 1080, "height": 1920},
        })
        self.assertEqual(status, 200)
        debug = body["debug"]
        self.assertTrue(debug["strategy"])
        self.assertIsInstance(debug["warnings"], list)
        legal = [row for row in debug["candidate_scores"] if row["legal"]]
        self.assertTrue(legal)
        for row in legal:
            self.assertEqual(set(row["breakdown"]), set(QUALITY_WEIGHTS))

    def test_preview_is_a_real_png_and_paths_cannot_escape(self):
        task = _sample("chameleon_sample_level1_warmup.json")
        _status, body = self._post("/api/resize", task)
        status, content_type, png = self._get(body["preview_url"])
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "image/png")
        self.assertTrue(png.startswith(b"\x89PNG"))
        for path in ("/api/previews/../app.py", "/api/previews/abc.png", "/api/previews/%2e%2e.png"):
            with self.subTest(path=path):
                self.assertEqual(self._get(path)[0], 404)

    def test_bad_requests_are_rejected_with_a_message(self):
        task = _sample("chameleon_sample_level1_warmup.json")
        source = task["source"]
        bad_asset = json.loads(json.dumps(source))
        next(e for e in bad_asset["elements"] if e["type"] == "image")["asset_id"] = "../secret.png"
        duplicate = json.loads(json.dumps(source))
        duplicate["elements"].append(dict(duplicate["elements"][0]))
        cases = {
            "not json": (None, b"{nope"),
            "not an object": ([1, 2], None),
            "zero width": ({"source": source, "target_canvas": {"width": 0, "height": 10}}, None),
            "huge canvas": ({"source": source, "target_canvas": {"width": 10**6, "height": 10}}, None),
            "path in asset id": ({"source": bad_asset, "target_canvas": task["target_canvas"]}, None),
            "duplicate id": ({"source": duplicate, "target_canvas": task["target_canvas"]}, None),
        }
        for label, (payload, raw) in cases.items():
            with self.subTest(case=label):
                status, body = self._post("/api/resize", payload, raw=raw)
                self.assertEqual(status, 400)
                self.assertTrue(body["error"])

    def test_missing_asset_still_renders(self):
        task = _sample("chameleon_sample_level3_advanced.json")
        status, body = self._post("/api/resize", task)
        self.assertEqual(status, 200)
        self.assertIsNotNone(body["preview_url"])

    def test_unknown_routes_are_404(self):
        self.assertEqual(self._get("/api/nope")[0], 404)
        self.assertEqual(self._post("/api/nope", {})[0], 404)


if __name__ == "__main__":
    unittest.main()
