"""Use real JKS files to protect persistent trust during initialization and retry."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import initialize_volume  # noqa: E402
import start_tak  # noqa: E402
from java_truststore import run  # noqa: E402


class InitializeVolumeTest(unittest.TestCase):
    def test_validated_seed_preserves_saved_trust_and_excludes_another_owner(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, CA_PASS="test-password"),
        ):
            work = Path(folder)
            certificate = work / "ca.pem"
            run(
                [
                    "openssl",
                    "req",
                    "-new",
                    "-x509",
                    "-newkey",
                    "ec",
                    "-pkeyopt",
                    "ec_paramgen_curve:P-256",
                    "-noenc",
                    "-keyout",
                    str(work / "ca.key"),
                    "-out",
                    str(certificate),
                    "-days",
                    "1",
                    "-subj",
                    "/CN=test-ca",
                ]
            )
            seed = work / "bootstrap.jks"
            run(
                [
                    "keytool",
                    "-importcert",
                    "-noprompt",
                    "-storetype",
                    "JKS",
                    "-keystore",
                    str(seed),
                    "-storepass:env",
                    "CA_PASS",
                    "-alias",
                    "ca",
                    "-file",
                    str(certificate),
                ]
            )
            root = work / "tak"
            initialize_volume.initialize(root, seed)
            saved = root / "data/certs/files/fed-truststore.jks"
            original = saved.read_bytes()
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
            seed.write_bytes(b"invalid bootstrap")
            initialize_volume.initialize(root, seed)
            self.assertEqual(saved.read_bytes(), original)
            lock, _ = start_tak.acquire_config_lock(root / "data")
            try:
                with self.assertRaisesRegex(RuntimeError, "already owns"):
                    initialize_volume.initialize(root, seed)
            finally:
                lock.close()
            with self.assertRaises(subprocess.CalledProcessError):
                initialize_volume.initialize(work / "fresh", seed)
            self.assertFalse(
                (work / "fresh/data/certs/files/fed-truststore.jks").exists()
            )
