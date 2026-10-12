"""Keep vendor routing and rotation while selecting the bundled ECS encoder."""

import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import logging_config  # noqa: E402


class LoggingConfigTest(unittest.TestCase):
    def test_vendor_destinations_and_policies_are_preserved(self) -> None:
        for profile in ("config", "messaging", "api", "retention", "pm"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                archive = (
                    "takserver.war"
                    if profile in ("config", "messaging", "api")
                    else f"takserver-{profile}.jar"
                )
                resource = (
                    "WEB-INF/classes/logback-spring.xml"
                    if archive.endswith("war")
                    else "BOOT-INF/classes/logback.xml"
                )
                (root / archive).symlink_to(Path("/opt/tak") / archive)
                with ZipFile(root / archive) as vendor:
                    original = ET.fromstring(vendor.read(resource))
                result = ET.parse(logging_config.configure(root, profile)).getroot()
                for tag in ("file", "rollingPolicy", "filter", "appender-ref"):
                    self.assertEqual(
                        [ET.tostring(e) for e in original.iter(tag)],
                        [ET.tostring(e) for e in result.iter(tag)],
                        tag,
                    )
                self.assertNotIn("scan", result.attrib)
                self.assertFalse(result.findall(".//layout"))
                encoders = result.findall(".//encoder")
                self.assertTrue(encoders)
                for encoder in encoders:
                    self.assertEqual(
                        encoder.get("class"),
                        "org.springframework.boot.logging.logback.StructuredLogEncoder",
                    )
                    self.assertEqual(encoder.findtext("format"), "ecs")

    def test_missing_vendor_encoders_fail(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with ZipFile(root / "takserver.war", "w") as archive:
                archive.writestr(
                    "WEB-INF/classes/logback-spring.xml", "<configuration/>"
                )
            with self.assertRaisesRegex(ValueError, "No logging encoders"):
                logging_config.configure(root, "api")
