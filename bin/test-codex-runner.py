#!/usr/bin/env python3
"""Exercise the real adapter process with a fake Codex CLI; no login or network."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

BIN = Path(__file__).resolve().parent


class CodexRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="watcher-codex-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        self.home = self.root / "watcher"
        for folder in ("commands", "agents"):
            (self.home / folder).mkdir(parents=True)
        (self.home / "commands/watch.md").write_text("---\ndescription: metadata\n---\nWork on $ARGUMENTS.\n")
        (self.home / "commands/triage.md").write_text("Triage $ARGUMENTS.\n")
        (self.home / "agents/reviewer.md").write_text("Review the exact commit.\n")
        (self.home / "agents/usability.md").write_text("Look at pictures only.\n")
        self.stub = self.root / "codex"
        self.stub.write_text("#!" + sys.executable + "\n" + textwrap.dedent('''\
            import json, os, pathlib, sys, time
            root = pathlib.Path(os.environ["FAKE_ROOT"])
            (root / "invocation.json").write_text(json.dumps({
                "args": sys.argv[1:], "prompt": sys.stdin.read(),
                "api_keys_present": any(k in os.environ for k in ("OPENAI_API_KEY", "CODEX_API_KEY"))
            }))
            mode = os.environ.get("FAKE_MODE", "success")
            if mode == "hang":
                (root / "child.pid").write_text(str(os.getpid()))
                time.sleep(30)
            def emit(e):
                print(json.dumps(e), flush=True)
            emit({"type":"thread.started", "thread_id":"thread-test"})
            emit({"type":"item.started", "item":{"id":"cmd-1", "type":"command_execution", "command":"git status"}})
            emit({"type":"item.completed", "item":{"id":"cmd-1", "type":"command_execution", "command":"git status", "aggregated_output":"clean", "exit_code":0}})
            emit({"type":"item.completed", "item":{"type":"agent_message", "text":"- Outcome: merged\\n- Ended in: Done\\n- Needs the owner: no"}})
            if mode == "malformed":
                print("not a JSON event", flush=True)
            if mode == "failed":
                emit({"type":"turn.failed", "error":{"message":"rate limited"}})
            elif mode != "incomplete":
                emit({"type":"turn.completed", "usage":{"input_tokens":100, "cached_input_tokens":40, "output_tokens":15}})
            sys.exit(23 if mode == "nonzero" else 0)
            '''))
        self.stub.chmod(0o755)
        self.env = {**os.environ, "WATCHER_HOME": str(self.home),
                    "WATCHER_CODEX": str(self.stub), "FAKE_ROOT": str(self.root),
                    "CLAUDE_PROJECTS_DIR": str(self.root / "transcripts"),
                    "OPENAI_API_KEY": "test-only-not-a-real-key",
                    "CODEX_API_KEY": "test-only-not-a-real-key"}
        self.env.pop("WATCHER_CODEX_MODEL", None)
        self.env.pop("WATCHER_CODEX_SANDBOX", None)

    def invoke(self, *args, mode="success"):
        return subprocess.run([sys.executable, str(BIN / "codex-runner.py"),
                               "--output-format", "json", *args],
                              cwd=self.project, env={**self.env, "FAKE_MODE": mode},
                              capture_output=True, text=True, timeout=10)

    def invocation(self):
        return json.loads((self.root / "invocation.json").read_text())

    def test_success_and_existing_log_readers(self):
        run = self.invoke("-p", "/watch 123", "--max-turns", "0", "--max-budget-usd", "0",
                          "--dangerously-skip-permissions")
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["subtype"], "success")
        self.assertEqual(result["usage"], {"input_tokens": 60, "cache_read_input_tokens": 40, "output_tokens": 15})
        self.assertIsNone(result["total_cost_usd"])
        self.assertEqual(result["codex_thread_id"], "thread-test")
        invocation = self.invocation()
        self.assertIn("Work on 123.", invocation["prompt"])
        self.assertNotIn("description: metadata", invocation["prompt"])
        self.assertFalse(invocation["api_keys_present"])
        self.assertIn('forced_login_method="chatgpt"', invocation["args"])
        self.assertIn('model_provider="openai"', invocation["args"])
        self.assertIn("workspace-write", invocation["args"])
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", invocation["args"])
        spec = importlib.util.spec_from_file_location("watcher_tail", BIN / "tail.py")
        tail = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tail)
        path = result["transcript_path"]
        lines, _ = tail.replay_lines(path)
        self.assertIn("$ git status", lines)
        self.assertIsNone(tail.current_step(path))
        self.assertEqual(tail.newest_jsonl([str(Path(path).parent)]), path)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_project_command_override_and_triage(self):
        overrides = self.project / ".claude/commands"
        overrides.mkdir(parents=True)
        (overrides / "triage.md").write_text("Project triage for $ARGUMENTS")
        run = self.invoke("-p", "/triage 8")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Project triage for 8", self.invocation()["prompt"])

    def test_explicit_model_and_isolated_host_sandbox(self):
        self.env.update(WATCHER_CODEX_MODEL="chosen-model", WATCHER_CODEX_SANDBOX="danger-full-access")
        run = self.invoke("-p", "/watch 9")
        self.assertEqual(run.returncode, 0, run.stderr)
        args = self.invocation()["args"]
        self.assertEqual(args[args.index("--model") + 1], "chosen-model")
        self.assertEqual(args[args.index("--sandbox") + 1], "danger-full-access")

    def test_failures_never_report_success(self):
        for mode in ("incomplete", "nonzero", "failed", "malformed"):
            with self.subTest(mode=mode):
                run = self.invoke("-p", "/watch 3", mode=mode)
                self.assertNotEqual(run.returncode, 0)
                self.assertTrue(json.loads(run.stdout)["is_error"])

    def test_unsupported_limits_and_unknown_commands_fail_before_launch(self):
        for args in (("-p", "/watch 1", "--max-budget-usd", "15"),
                     ("-p", "/watch 1", "--max-turns", "400"),
                     ("-p", "/missing 1"), ("-p", "/../../secret 1")):
            with self.subTest(args=args):
                run = self.invoke(*args)
                self.assertNotEqual(run.returncode, 0)
                self.assertFalse((self.root / "invocation.json").exists())

    def test_missing_codex_explains_login_requirement(self):
        self.env["WATCHER_CODEX"] = str(self.root / "missing")
        run = self.invoke("-p", "/watch 1")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("Codex CLI not found", run.stderr)

    def test_reviewer_runs_separately_read_only_even_on_full_access_lane(self):
        builder = self.invoke("-p", "/watch 1")
        builder_path = json.loads(builder.stdout)["transcript_path"]
        context = self.root / "review.txt"
        context.write_text("Review commit abc123; inspect the diff.")
        self.env["WATCHER_CODEX_SANDBOX"] = "danger-full-access"
        run = self.invoke("--agent", "reviewer", "--context-file", str(context))
        self.assertEqual(run.returncode, 0, run.stderr)
        invocation = self.invocation()
        self.assertIn("read-only", invocation["args"])
        self.assertIn("--ignore-user-config", invocation["args"])
        self.assertIn("independent reviewer", invocation["prompt"])
        self.assertIn("Review commit abc123", invocation["prompt"])
        reviewer_path = json.loads(run.stdout)["transcript_path"]
        self.assertEqual(Path(reviewer_path).parent.name, "reviews")
        spec = importlib.util.spec_from_file_location("watcher_tail", BIN / "tail.py")
        tail = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tail)
        self.assertEqual(tail.newest_jsonl(str(Path(builder_path).parent)), builder_path)

    def test_usability_gets_pictures_and_empty_working_directory(self):
        context = self.root / "visual.txt"
        context.write_text("Ask: show the result. SHA: abc123")
        image = self.root / "phone.png"
        image.write_bytes(b"fixture-only")
        run = self.invoke("--agent", "usability", "--context-file", str(context), "--image", str(image))
        self.assertEqual(run.returncode, 0, run.stderr)
        args = self.invocation()["args"]
        self.assertIn("features.shell_tool=false", args)
        self.assertIn("read-only", args)
        self.assertIn("--skip-git-repo-check", args)
        self.assertNotEqual(args[args.index("--cd") + 1], str(self.project))
        self.assertIn(str(image), args)

    def test_usability_refuses_without_pictures(self):
        context = self.root / "visual.txt"
        context.write_text("Ask: show the result. SHA: abc123")
        run = self.invoke("--agent", "usability", "--context-file", str(context))
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("requires at least one --image", run.stderr)

    def test_signal_stops_codex_and_writes_failed_result(self):
        proc = subprocess.Popen([sys.executable, str(BIN / "codex-runner.py"),
                                 "-p", "/watch 4", "--output-format", "json"],
                                cwd=self.project, env={**self.env, "FAKE_MODE": "hang"},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            pidfile = self.root / "child.pid"
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(pidfile.exists())
            child = int(pidfile.read_text())
            proc.send_signal(signal.SIGTERM)
            stdout, _ = proc.communicate(timeout=8)
            self.assertNotEqual(proc.returncode, 0)
            self.assertTrue(json.loads(stdout)["is_error"])
            with self.assertRaises(ProcessLookupError):
                os.kill(child, 0)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
