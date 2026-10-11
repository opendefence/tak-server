"""Configuration-service ownership and shared startup behavior."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import coreconfig  # noqa: E402
import start_tak  # noqa: E402
from lxml import etree  # noqa: E402


class StartupTest(unittest.TestCase):
    """Exercise shared files and readiness without requiring a running database."""

    def setUp(self) -> None:
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.data = self.root / "data"
        self.data.mkdir()

    def test_readiness_requires_current_live_owner(self) -> None:
        (self.data / ".coreconfig-ready").write_text("stale")
        with self.assertRaises(TimeoutError):
            start_tak.wait_for_configuration(self.data, timeout=0)

        lock, generation = start_tak.acquire_config_lock(self.data)
        self.addCleanup(lock.close)
        self.assertTrue(os.get_inheritable(lock.fileno()))
        with self.assertRaises(RuntimeError):
            start_tak.acquire_config_lock(self.data)
        with self.assertRaises(TimeoutError):
            start_tak.wait_for_configuration(self.data, timeout=0)
        coreconfig.atomic_write(self.data / ".coreconfig-ready", generation.encode())
        start_tak.wait_for_configuration(self.data, timeout=0)
        lock.close()
        with self.assertRaises(TimeoutError):
            start_tak.wait_for_configuration(self.data, timeout=0)

    def test_strict_mode_requires_the_agent_before_storage_changes(self) -> None:
        with (
            patch.dict(os.environ, TAK_AUTH_MODE="strict"),
            patch.object(sys, "argv", ["start_tak.py", "api"]),
            patch.object(Path, "is_file", return_value=False),
            self.assertRaisesRegex(RuntimeError, "Strict authentication injection"),
        ):
            start_tak.main()

    def test_prepares_one_authority_and_preserves_admin_restart_changes(self) -> None:
        shutil.copy("/opt/tak/CoreConfig.xsd", self.root / "CoreConfig.xsd")
        templates = Path(__file__).resolve().parents[1] / "templates"
        environment = {
            "TAKSERVER_CERT_PASS": "test",  # pragma: allowlist secret
            "CA_PASS": "test",  # pragma: allowlist secret
            "POSTGRES_USER": "tak",
            "POSTGRES_PASSWORD": "test",  # pragma: allowlist secret
            "TAK_SERVER_ADDRESS": "tak.test",
        }
        with patch.dict(os.environ, environment):
            start_tak.prepare_configuration(self.root, templates)
            canonical = self.data / "CoreConfig_config.xml"
            common = self.data / "CoreConfig.xml"
            self.assertEqual(common.resolve(), canonical)
            self.assertFalse((self.data / "TAKIgniteConfig.xml").exists())
            saved = coreconfig.read_xml(canonical)
            coreconfig.require(saved, "federation").set(
                "allowMissionFederation", "false"
            )
            from lxml import etree

            canonical.write_bytes(etree.tostring(saved))
            start_tak.prepare_configuration(self.root, templates)
            self.assertEqual(
                coreconfig.require(coreconfig.read_xml(common), "federation").get(
                    "allowMissionFederation"
                ),
                "false",
            )
            start_tak.link_file(self.root / "CoreConfig.xml", canonical)
            self.assertEqual((self.root / "CoreConfig.xml").resolve(), canonical)
            self.assertFalse((self.data / "CoreConfig_api.xml").exists())

    def test_xml_attribute_inputs_are_literal_values(self) -> None:
        shutil.copy("/opt/tak/CoreConfig.xsd", self.root / "CoreConfig.xsd")
        password = "test&<\"'>"  # pragma: allowlist secret
        environment = {
            "TAKSERVER_CERT_PASS": password,
            "CA_PASS": password,
            "POSTGRES_USER": 'tak&"user',
            "POSTGRES_PASSWORD": password,
            "TAK_SERVER_ADDRESS": "tak.test",
            "LDAP_BIND_PASSWORD": "",
        }
        with patch.dict(os.environ, environment):
            start_tak.prepare_configuration(
                self.root, Path(__file__).resolve().parents[1] / "templates"
            )
        saved = coreconfig.read_xml(self.data / "CoreConfig_config.xml")
        self.assertEqual(
            coreconfig.require(saved, "repository/connection").get("password"),
            password,
        )
        self.assertEqual(
            coreconfig.require(saved, "security/tls").get("keystorePass"), password
        )

    def test_vendor_cluster_mode_cannot_move_the_authority(self) -> None:
        canonical = self.data / "CoreConfig_config.xml"
        saved = (
            b'<Configuration xmlns="http://bbn.com/marti/xml/config">'
            b'<cluster enabled="true"/></Configuration>'
        )
        canonical.write_bytes(saved)
        with self.assertRaisesRegex(ValueError, "TAK cluster mode"):
            start_tak.prepare_configuration(self.root, self.root / "templates")
        self.assertEqual(canonical.read_bytes(), saved)

    def test_legacy_authentication_is_preserved_and_invalid_state_is_rejected(
        self,
    ) -> None:
        shutil.copy(
            "/opt/tak/UserAuthenticationFile.xsd",
            self.root / "UserAuthenticationFile.xsd",
        )
        legacy = self.data / "UserAuthenticationFile.xml"
        original = (
            b'<UserAuthenticationFile xmlns="http://bbn.com/marti/xml/bindings">'
            b'<User identifier="account-a"/></UserAuthenticationFile>'
        )
        legacy.write_bytes(original)
        (self.data / "UserAuthenticationFile.xml.backup").write_bytes(original)
        start_tak.prepare_authentication(self.root)
        authority = self.data / "auth/UserAuthenticationFile.xml"
        backup = authority.with_name(authority.name + ".backup")
        self.assertEqual(authority.read_bytes(), original)
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(authority.stat().st_mode & 0o777, 0o600)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        updated = original.replace(b"account-a", b"account-b")
        authority.write_bytes(updated)
        start_tak.prepare_authentication(self.root)
        self.assertEqual(authority.read_bytes(), updated)
        self.assertEqual(legacy.read_bytes(), original)
        authority.write_bytes(b"broken XML")
        with self.assertRaises(etree.LxmlError):
            start_tak.prepare_authentication(self.root)
        self.assertEqual(authority.read_bytes(), b"broken XML")
        self.assertEqual(backup.read_bytes(), original)

    def test_api_writes_are_private_and_owner_backup_is_persistent(self) -> None:
        canonical = self.data / "CoreConfig_config.xml"
        canonical.write_bytes(b"saved CoreConfig")
        auth = self.data / "auth/UserAuthenticationFile.xml"
        auth.parent.mkdir()
        auth.write_bytes(b"saved file-auth")
        for profile in ("config", "messaging", "api", "pm", "retention"):
            root = self.root / profile
            root.mkdir()
            (root / "data").symlink_to(self.data)
            runtime = root / "runtime" / profile
            runtime.mkdir(parents=True)
            if profile == "config":
                (root / "CoreConfig.xml.backup").write_bytes(b"old owner backup")
            start_tak.prepare_role_files(root, profile, runtime)
            if profile == "config":
                self.assertEqual((root / "CoreConfig.xml").resolve(), canonical)
                self.assertEqual(
                    (root / "CoreConfig.xml.backup").resolve(),
                    self.data / "CoreConfig_config.xml.backup",
                )
                self.assertEqual(
                    (root / "CoreConfig.xml.backup").read_bytes(), b"old owner backup"
                )
            else:
                (root / "CoreConfig.xml").write_bytes(b"follower defaults")
                (root / "CoreConfig.xml.backup").write_bytes(b"follower backup")
                self.assertEqual(canonical.read_bytes(), b"saved CoreConfig")
            if profile in ("config", "messaging"):
                self.assertEqual(
                    (root / "auth/UserAuthenticationFile.xml").resolve(), auth
                )
            else:
                (root / "auth/UserAuthenticationFile.xml").write_bytes(
                    b"private update"
                )
                (root / "auth/UserAuthenticationFile.xml.backup").write_bytes(
                    b"private backup"
                )
                self.assertEqual(auth.read_bytes(), b"saved file-auth")
                self.assertFalse(
                    (self.data / "auth/UserAuthenticationFile.xml.backup").exists()
                )


if __name__ == "__main__":
    unittest.main()
