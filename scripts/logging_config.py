"""Use Spring's bundled ECS encoder without changing vendor log routing."""

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


def configure(root: Path, profile: str) -> Path:
    if profile in ("config", "messaging", "api"):
        archive, resource = "takserver.war", "WEB-INF/classes/logback-spring.xml"
    else:
        archive, resource = f"takserver-{profile}.jar", "BOOT-INF/classes/logback.xml"
    with ZipFile(root / archive) as vendor:
        tree = ET.fromstring(vendor.read(resource))
    # Spring extensions cannot be reloaded by Logback's native file scanner.
    tree.attrib.pop("scan", None)
    tree.attrib.pop("scanPeriod", None)
    encoders = tree.findall(".//encoder") + tree.findall(".//appender/if/then/layout")
    if not encoders:
        raise ValueError(f"No logging encoders in {archive}")
    for encoder in encoders:
        encoder.clear()
        encoder.tag = "encoder"
        encoder.set(
            "class", "org.springframework.boot.logging.logback.StructuredLogEncoder"
        )
        ET.SubElement(encoder, "format").text = "ecs"
    destination = root / "runtime" / profile / "logback-ecs.xml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(tree).write(destination, encoding="utf-8", xml_declaration=True)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile", choices=("config", "messaging", "api", "retention", "pm")
    )
    print(configure(Path("/opt/tak"), parser.parse_args().profile))
