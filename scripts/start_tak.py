"""Prepare shared configuration once and launch a TAK service."""

import argparse
import fcntl
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import TextIO
from xml.sax.saxutils import escape

import coreconfig
import ignite_config
import java_truststore
from lxml import etree


def link_file(link: Path, target: Path) -> None:
    """Atomically replace a compatibility link."""
    with tempfile.TemporaryDirectory(prefix=".config-link-", dir=link.parent) as folder:
        temporary = Path(folder) / "link"
        temporary.symlink_to(target)
        os.replace(temporary, link)


def prepare_configuration(root: Path, templates: Path) -> None:
    """Only the configuration service updates files in the shared volume."""
    data = root / "data"
    canonical = data / "CoreConfig_config.xml"
    common = data / "CoreConfig.xml"
    source = canonical if canonical.exists() else common
    if source.exists():
        cluster = coreconfig.one(coreconfig.read_xml(source), "cluster")
        if cluster is not None and cluster.get("enabled") in ("true", "1"):
            raise ValueError(
                "TAK cluster mode changes the authority path and is unsupported"
            )
    with tempfile.TemporaryDirectory(prefix=".config-render-", dir=data) as folder:
        rendered = Path(folder) / "CoreConfig.xml"
        environment = dict(os.environ)
        for key, value in environment.items():
            if (
                key.startswith(("TAK", "POSTGRES_", "LDAP_", "WEBTAK_"))
                or key == "CA_PASS"
            ):
                environment[key] = escape(value, {'"': "&quot;", "'": "&apos;"})
        with rendered.open("wb") as stream:
            subprocess.run(
                ["gomplate", "-f", str(templates / "CoreConfig.tpl")],
                env=environment,
                stdout=stream,
                check=True,
            )
        coreconfig.prepare(rendered, canonical, root / "CoreConfig.xsd", common)

    backup = data / "CoreConfig.xml.pre-authority-backup"
    if common.exists() and not common.is_symlink() and not backup.exists():
        coreconfig.atomic_write(backup, common.read_bytes())
    link_file(common, canonical)


def prepare_authentication(root: Path) -> None:
    """Adopt legacy file-auth without overwriting a current messaging authority."""
    directory = root / "data/auth"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    destination = directory / "UserAuthenticationFile.xml"
    legacy = root / "data/UserAuthenticationFile.xml"
    source = destination if destination.exists() else legacy
    data = (
        source.read_bytes()
        if source.exists()
        else b'<UserAuthenticationFile xmlns="http://bbn.com/marti/xml/bindings"/>\n'
    )
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    tree = etree.fromstring(data, parser)
    if tree.getroottree().docinfo.doctype:
        raise ValueError("DOCTYPE is not allowed in file-auth state")
    etree.XMLSchema(etree.parse(str(root / "UserAuthenticationFile.xsd"))).assertValid(
        tree
    )
    if not destination.exists():
        coreconfig.atomic_write(destination, data)
        legacy_backup = legacy.with_name(legacy.name + ".backup")
        if legacy_backup.exists():
            coreconfig.atomic_write(
                destination.with_name(destination.name + ".backup"),
                legacy_backup.read_bytes(),
            )
    backup = destination.with_name(destination.name + ".backup")
    for path in (
        destination,
        backup,
        legacy,
        legacy.with_name(legacy.name + ".backup"),
    ):
        if path.exists():
            path.chmod(0o600)


def prepare_role_files(root: Path, profile: str, runtime: Path) -> Path:
    """Keep follower XML and file-auth saves out of the persistent authorities."""
    canonical = root / "data/CoreConfig_config.xml"
    local = canonical
    if profile != "config":
        local = runtime / "CoreConfig.xml"
        coreconfig.atomic_write(local, canonical.read_bytes())
    link_file(root / "CoreConfig.xml", local)
    backup = local.with_name(local.name + ".backup")
    old_backup = root / "CoreConfig.xml.backup"
    if (
        profile == "config"
        and old_backup.is_file()
        and not old_backup.is_symlink()
        and not backup.exists()
    ):
        coreconfig.atomic_write(backup, old_backup.read_bytes())
    link_file(old_backup, backup)
    authority = root / "data/auth"
    auth = authority
    if profile not in ("config", "messaging"):
        auth = runtime / "auth"
        auth.mkdir(mode=0o700, exist_ok=True)
        coreconfig.atomic_write(
            auth / "UserAuthenticationFile.xml",
            (authority / "UserAuthenticationFile.xml").read_bytes(),
        )
    link_file(root / "auth", auth)
    return local


def acquire_config_lock(data: Path) -> tuple[TextIO, str]:
    """Hold exclusive ownership until the configuration JVM exits."""
    lock = (data / ".coreconfig-service.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError(
            "Another TAK configuration service already owns this volume"
        ) from None
    generation = uuid.uuid4().hex
    lock.seek(0)
    lock.truncate()
    lock.write(generation)
    lock.flush()
    os.fsync(lock.fileno())
    os.set_inheritable(lock.fileno(), True)
    return lock, generation


def wait_for_configuration(data: Path, timeout: float = 180) -> None:
    """Wait for the current config service, ignoring readiness left by an older run."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            with (data / ".coreconfig-service.lock").open() as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
                except BlockingIOError:
                    generation = lock.read()
                    ready = (data / ".coreconfig-ready").read_text()
                    if generation and generation == ready:
                        return
        except FileNotFoundError:
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "TAK configuration service did not prepare the shared configuration"
            )
        time.sleep(0.2)


def main() -> None:
    """Keep the ownership lock across exec; followers never render shared XML."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile", choices=("config", "messaging", "api", "retention", "pm")
    )
    args = parser.parse_args()
    mode = os.environ.get("TAK_AUTH_MODE", "legacy")
    if mode not in ("legacy", "strict") or (
        mode == "strict"
        and not Path("/opt/tak/lib/strict-fingerprint-agent.jar").is_file()
    ):
        raise RuntimeError(
            "Strict authentication injection is unavailable; select a supported mode"
        )
    os.umask(0o077)
    root = Path("/opt/tak")
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    if args.profile == "config":
        lock, generation = acquire_config_lock(data)
        # Keep the descriptor open through exec and throughout the JVM lifetime.
        try:
            prepare_authentication(root)
            prepare_configuration(root, Path("/opt/templates"))
            coreconfig.atomic_write(data / ".coreconfig-ready", generation.encode())
        except BaseException:
            lock.close()
            raise
    else:
        wait_for_configuration(data)
    ignite = ignite_config.prepare(root, Path("/opt/templates"), args.profile)
    local = prepare_role_files(root, args.profile, ignite.parent)
    link_file(root / "TAKIgniteConfig.xml", ignite)
    os.environ["TAKCL_CORECONFIG_PATH"] = str(local)
    java_truststore.configure(root, runtime=ignite.parent)
    os.execv("/bin/bash", ["/bin/bash", "/opt/scripts/run-tak.sh", args.profile])


if __name__ == "__main__":
    main()
