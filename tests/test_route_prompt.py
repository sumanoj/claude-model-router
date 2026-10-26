"""Tests for the prompt classifier. Run: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "plugins", "model-router", "scripts", "route_prompt.py")
sys.path.insert(0, os.path.dirname(HOOK))
from route_prompt import classify  # noqa: E402


class ClassifyTests(unittest.TestCase):
    def tier(self, prompt):
        return classify(prompt)[0]

    def test_fast(self):
        self.assertEqual(self.tier("fix the typo in README"), "fast")
        self.assertEqual(self.tier("where is the config loaded?"), "fast")
        self.assertEqual(self.tier("rename foo to bar in utils.py"), "fast")

    def test_standard(self):
        self.assertEqual(self.tier("add a /health endpoint to the Flask app and write a test for it"), "standard")
        self.assertEqual(self.tier("the login form doesn't show an error when the password is wrong, fix it"), "standard")

    def test_deep(self):
        self.assertEqual(self.tier("design a RAG pipeline architecture for 10M documents with trade-offs"), "deep")
        self.assertEqual(self.tier("find the root cause of this intermittent race condition in the worker pool"), "deep")
        self.assertEqual(self.tier("refactor the auth module across all services and plan the migration"), "deep")

    def test_codex(self):
        self.assertEqual(self.tier("ask codex to review this function"), "codex")
        self.assertEqual(self.tier("get a second opinion on this design"), "codex")


class HookIOTests(unittest.TestCase):
    def run_hook(self, payload):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home)
            out = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True,
                                 text=True, env=env, check=True)
            log = os.path.join(home, ".claude", "router-log.jsonl")
            return out.stdout, os.path.exists(log)

    def test_emits_context_and_logs(self):
        stdout, logged = self.run_hook(json.dumps({"prompt": "fix the typo"}))
        data = json.loads(stdout)
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("model-router:router-fast", data["hookSpecificOutput"]["additionalContext"])
        self.assertTrue(logged)

    def test_bad_input_is_silent(self):
        stdout, _ = self.run_hook("not json")
        self.assertEqual(stdout, "")


if __name__ == "__main__":
    unittest.main()
