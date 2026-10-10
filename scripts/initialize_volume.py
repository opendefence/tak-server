"""Prepare persistent directories and seed federation trust without local CA keys."""

import os
import subprocess
from pathlib import Path

import coreconfig
import start_tak


def initialize(root: Path, bootstrap: Path) -> None:
    data = root / "data"
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock, _ = start_tak.acquire_config_lock(data)
    with lock:
        for name in ("auth", "logs", "certs/files"):
            (data / name).mkdir(mode=0o700, parents=True, exist_ok=True)
        destination = data / "certs/files/fed-truststore.jks"
        source = destination if destination.exists() else bootstrap
        subprocess.run(
            ["keytool", "-list", "-keystore", str(source), "-storepass:env", "CA_PASS"],
            capture_output=True,
            check=True,
        )
        if not destination.exists():
            coreconfig.atomic_write(destination, source.read_bytes())
        destination.chmod(0o600)


if __name__ == "__main__":
    os.umask(0o077)
    initialize(Path("/opt/tak"), Path("/identities/federation/truststore.jks"))
