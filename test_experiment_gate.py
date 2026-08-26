"""Tests for the human freeze gate.

Each test builds a throwaway git repository and drives the real git binary, because the
gate's whole value is what git will and will not attest to. The launch-blocking paths
matter most: a dirty tree, an uncommitted stamp, a swapped run name, and a preregistration
re-committed after stamping must all abort.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import experiment_gate


class ExperimentGateTest(unittest.TestCase):
    PREREG = os.path.join("Experiments", "PREREGISTRATION_DEMO.md")
    RUN = "trackX_demo_Python"

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="gate_test_")
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self._original_root = experiment_gate.REPO_ROOT
        experiment_gate.REPO_ROOT = self.repo
        self.addCleanup(setattr, experiment_gate, "REPO_ROOT", self._original_root)
        self._git("init", "-q")
        self._git("config", "user.email", "gate-test@example.invalid")
        self._git("config", "user.name", "Gate Test")
        self._git("config", "commit.gpgsign", "false")
        os.makedirs(os.path.join(self.repo, "Experiments"))
        self._write("README.md", "base\n")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "base")

    def _git(self, *args):
        subprocess.run(["git", "-C", self.repo, *args], check=True,
                       capture_output=True, text=True)

    def _write(self, relative, content):
        path = os.path.join(self.repo, relative)
        os.makedirs(os.path.dirname(path) or self.repo, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        return path

    def _stamp(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return experiment_gate.stamp(self.PREREG, self.RUN)

    def _commit_all(self, message):
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message)

    def test_stamp_refuses_dirty_tree(self):
        self._write(self.PREREG, "protocol v1\n")  # exists but is untracked
        with self.assertRaises(experiment_gate.GateError) as ctx:
            self._stamp()
        self.assertIn("uncommitted", str(ctx.exception))

    def test_stamp_records_committed_blob_and_sha256(self):
        path = self._write(self.PREREG, "protocol v1\n")
        self._commit_all("freeze protocol")
        stamp_file = self._stamp()
        with open(os.path.join(self.repo, stamp_file), encoding="utf-8") as handle:
            record = json.load(handle)
        self.assertEqual(record["run_name"], self.RUN)
        self.assertEqual(record["preregistration"], self.PREREG.replace(os.sep, "/"))
        self.assertEqual(record["prereg_git_blob"],
                         experiment_gate.committed_blob(path))
        with open(path, "rb") as handle:
            self.assertEqual(record["prereg_sha256"],
                             hashlib.sha256(handle.read()).hexdigest())
        self.assertEqual(record["stamped_at_head"], experiment_gate.head_commit())

    def test_check_blocks_uncommitted_stamp(self):
        self._write(self.PREREG, "protocol v1\n")
        self._commit_all("freeze protocol")
        stamp_file = self._stamp()  # stamp written but not committed -> tree is dirty
        with self.assertRaises(experiment_gate.GateError) as ctx:
            experiment_gate.check(stamp_file, self.RUN)
        self.assertIn("BLOCKED", str(ctx.exception))

    def test_check_passes_committed_stamp_and_blocks_wrong_run(self):
        self._write(self.PREREG, "protocol v1\n")
        self._commit_all("freeze protocol")
        stamp_file = self._stamp()
        self._commit_all("commit freeze stamp")
        record = experiment_gate.check(stamp_file, self.RUN)
        self.assertTrue(record["working_tree_clean"])
        self.assertEqual(record["verified_at_head"], experiment_gate.head_commit())
        with self.assertRaises(experiment_gate.GateError) as ctx:
            experiment_gate.check(stamp_file, "trackY_other_Python")
        self.assertIn("single-use", str(ctx.exception))

    def test_check_blocks_prereg_edits_dirty_or_recommitted(self):
        self._write(self.PREREG, "protocol v1\n")
        self._commit_all("freeze protocol")
        stamp_file = self._stamp()
        self._commit_all("commit freeze stamp")
        self._write(self.PREREG, "protocol v2 -- quietly relaxed\n")
        with self.assertRaises(experiment_gate.GateError):
            experiment_gate.check(stamp_file, self.RUN)  # dirty tree
        self._commit_all("relax protocol after freeze")
        with self.assertRaises(experiment_gate.GateError) as ctx:
            experiment_gate.check(stamp_file, self.RUN)  # clean, but blob moved
        self.assertIn("re-committed after stamping", str(ctx.exception))
        # Recovery is a fresh stamp of the new protocol, itself committed.
        stamp_file = self._stamp()
        self._commit_all("re-freeze protocol v2")
        self.assertTrue(experiment_gate.check(stamp_file, self.RUN)["working_tree_clean"])

    def test_git_provenance_reports_errors_as_data(self):
        state = experiment_gate.git_provenance()
        self.assertTrue(state["working_tree_clean"])
        self._write("scratch.txt", "dirt\n")
        state = experiment_gate.git_provenance()
        self.assertFalse(state["working_tree_clean"])
        self.assertEqual(state["dirty_paths"], 1)
        not_a_repo = tempfile.mkdtemp(prefix="gate_norepo_")
        self.addCleanup(shutil.rmtree, not_a_repo, ignore_errors=True)
        experiment_gate.REPO_ROOT = not_a_repo
        self.assertIn("error", experiment_gate.git_provenance())


if __name__ == "__main__":
    unittest.main()
