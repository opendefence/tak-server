"""Select bundled logging encoders without changing vendor log routing."""

import argparse
import os
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


def configure(root: Path, profile: str, log_format: str = "utc") -> Path:
    if log_format not in ("ecs", "utc", "local"):
        raise ValueError("TAK_LOG_FORMAT must be ecs, utc, or local")
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
        if log_format == "ecs":
            encoder.set(
                "class", "org.springframework.boot.logging.logback.StructuredLogEncoder"
            )
            ET.SubElement(encoder, "format").text = "ecs"
        else:
            encoder.set("class", "ch.qos.logback.classic.encoder.PatternLayoutEncoder")
            date = (
                "yyyy-MM-dd'T'HH:mm:ss.SSS'Z',UTC"
                if log_format == "utc"
                else "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"
            )
            ET.SubElement(encoder, "pattern").text = (
                f"[%d{{{date}}}][%level] %logger "
                r"\(${PID:-unknown}\) %file:%method:%line | %msg %mdc%n%ex"
            )
    if log_format != "ecs":
        # Capture the caller before handing the event to an asynchronous worker.
        for appender in tree.findall(".//appender"):
            if appender.get("class") == "ch.qos.logback.classic.AsyncAppender":
                caller = appender.find("includeCallerData")
                if caller is None:
                    caller = ET.SubElement(appender, "includeCallerData")
                caller.text = "true"
    destination = root / "runtime" / profile / "logback.xml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(tree).write(destination, encoding="utf-8", xml_declaration=True)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile", choices=("config", "messaging", "api", "retention", "pm")
    )
    print(
        configure(
            Path("/opt/tak"),
            parser.parse_args().profile,
            os.environ.get("TAK_LOG_FORMAT", "utc"),
        )
    )
