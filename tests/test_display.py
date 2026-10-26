"""Tests for the router display: systemMessage, delegation tracking, status line, stats.
Run: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
HOOKS = os.path.join(ROOT, ".claude", "hooks")
ROUTE = os.path.join(HOOKS, "route_prompt.py")
TRACK = os.path.join(HOOKS, "track_delegation.py")
STATUS = os.path.join(HOOKS, "statusline.py")
STATS = os.path.join(ROOT, "router_stats.py")


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ, HOME=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, script, payload, args=()):
        out = subprocess.run([sys.executable, script, *args], input=json.dumps(payload),
                             capture_output=True, text=True, env=self.env, check=True)
        return out.stdout

    def prompt(self, text, session="s1"):
        return json.loads(self.run_script(ROUTE, {"prompt": text, "session_id": session}))

    def delegate(self, agent, session="s1"):
        out = self.run_script(TRACK, {"tool_name": "Agent", "session_id": session,
                                      "tool_input": {"subagent_type": agent}})
        return json.loads(out)["systemMessage"]

    def status(self, session="s1"):
        return self.run_script(STATUS, {"session_id": session,
                                        "model": {"display_name": "Sonnet 5.5"}}).strip()

    def test_prompt_shows_system_message(self):
        data = self.prompt("fix the typo in README")
        self.assertEqual(data["systemMessage"], "Router: fast -> router-fast (Haiku 5.5, low effort)")

    def test_status_line_lifecycle(self):
        self.assertEqual(self.status(), "Sonnet 5.5 | router: no prompt classified yet")
        self.prompt("fix the typo in README")
        self.assertEqual(self.status(), "Sonnet 5.5 | router: fast -> router-fast | ran: waiting")
        self.assertIn("matches hint", self.delegate("router-fast"))
        self.assertEqual(self.status(), "Sonnet 5.5 | router: fast -> router-fast | ran: router-fast (ok)")

    def test_override_is_flagged(self):
        self.prompt("fix the typo in README")
        self.assertIn("hint was router-fast", self.delegate("router-deep"))
        self.assertTrue(self.status().endswith("ran: router-deep (override)"))

    def test_new_prompt_resets_ran(self):
        self.prompt("fix the typo in README")
        self.delegate("router-fast")
        self.prompt("design a RAG pipeline architecture with trade-offs")
        self.assertTrue(self.status().endswith("router: deep -> router-deep | ran: waiting"))

    def test_sessions_are_separate(self):
        self.prompt("fix the typo in README", session="a")
        self.assertIn("no prompt classified yet", self.status(session="b"))

    def test_task_notification_is_not_classified(self):
        self.prompt("fix the typo in README")
        self.delegate("router-fast")
        note = "<task-notification>\n<task-id>abc</task-id>\n" + "result text " * 100
        out = self.run_script(ROUTE, {"prompt": note, "session_id": "s1"})
        self.assertEqual(out, "")
        self.assertTrue(self.status().endswith("ran: router-fast (ok)"))

    def test_other_tools_ignored(self):
        self.assertEqual(self.run_script(TRACK, {"tool_name": "Bash", "session_id": "s1"}), "")

    def test_stats_report(self):
        self.prompt("fix the typo in README")
        self.delegate("router-fast")
        self.prompt("design a RAG pipeline architecture with trade-offs")
        self.delegate("router-standard")
        report = self.run_script(STATS, {})
        self.assertIn("Prompts classified: 2", report)
        self.assertIn("followed hint: 1/2 (50%)", report)
        self.assertIn("hint was router-deep", report)


if __name__ == "__main__":
    unittest.main()
