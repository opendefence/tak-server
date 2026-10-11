"""A live sibling or open socket must not hide a failed role or remote service."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import healthcheck  # noqa: E402


class HealthcheckTest(unittest.TestCase):
    def test_exiting_process_does_not_hide_a_live_jvm(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            exited = root / "proc/12/comm"
            java = root / "proc/13/comm"
            for path in (exited, java):
                path.parent.mkdir(parents=True)
                path.write_text("java\n")
            with (
                patch.dict(os.environ, TAK_SERVER_ADDRESS="tak.test"),
                patch.object(healthcheck.start_tak, "wait_for_configuration"),
                patch.object(Path, "glob", return_value=[exited, java]),
                patch.object(
                    Path, "read_text", side_effect=[FileNotFoundError(), "java\n"]
                ),
                patch.object(healthcheck.subprocess, "run") as request,
            ):
                request.return_value = subprocess.CompletedProcess([], 0, b"{}")
                healthcheck.check("api", root, root / "proc")
                request.assert_called_once()

    def test_local_jvm_and_authenticated_remote_read_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            proc = root / "proc"
            (proc / "12").mkdir(parents=True)
            comm = proc / "12/comm"
            comm.write_text("java\n")
            with (
                patch.dict(os.environ, TAK_SERVER_ADDRESS="tak.test"),
                patch.object(healthcheck.start_tak, "wait_for_configuration"),
                patch.object(healthcheck.subprocess, "run") as request,
            ):
                request.return_value = subprocess.CompletedProcess([], 0, b"{}")
                healthcheck.check("api", root, proc)
                self.assertEqual(request.call_count, 1)
                https = request.call_args
                self.assertIn("--fail", https.args[0])
                self.assertIn("--cacert", https.args[0])
                self.assertNotIn("--insecure", https.args[0])
                self.assertEqual(https.kwargs["timeout"], 4)
                request.reset_mock()
                comm.write_text("bash\n")
                with self.assertRaisesRegex(RuntimeError, "local TAK JVM"):
                    healthcheck.check("config", root, proc)
                request.assert_not_called()
                comm.write_text("java\n")
                for failure in (
                    subprocess.CalledProcessError(22, "curl"),
                    subprocess.TimeoutExpired("curl", 4),
                ):
                    request.side_effect = failure
                    with self.assertRaisesRegex(RuntimeError, "messaging read failed"):
                        healthcheck.check("messaging", root, proc)
                request.side_effect = None
                request.return_value = subprocess.CompletedProcess([], 0, b"not JSON")
                with self.assertRaisesRegex(RuntimeError, "messaging read failed"):
                    healthcheck.check("api", root, proc)
