"""Check the local JVM, configuration ownership, and authenticated messaging RPC."""

import argparse
import json
import os
import subprocess
from pathlib import Path

import start_tak


def check(
    profile: str,
    root: Path = Path("/opt/tak"),
    proc: Path = Path("/proc"),
) -> None:
    """A shared Pod socket cannot prove that this container's JVM is alive."""
    start_tak.wait_for_configuration(root / "data", timeout=0)
    for path in proc.glob("[0-9]*/comm"):
        try:
            if path.read_text().strip() == "java":
                break
        except FileNotFoundError:
            continue
    else:
        raise RuntimeError("The local TAK JVM is not running")
    if profile == "pm" and not (root / "runtime/pm/ready").exists():
        raise RuntimeError("The plugin application has not completed startup")
    host = os.environ["TAK_SERVER_ADDRESS"]
    if not host or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        for character in host
    ):
        raise ValueError("TAK_SERVER_ADDRESS must be a DNS name for the HTTPS probe")
    try:
        result = subprocess.run(
            [
                "curl",
                "--silent",
                "--fail",
                "--noproxy",
                "*",
                "--connect-timeout",
                "2",
                "--max-time",
                "3",
                "--resolve",
                f"{host}:8443:127.0.0.1",
                "--cacert",
                "/probe/ca.crt",
                "--cert",
                "/probe/tls.crt",
                "--key",
                "/probe/tls.key",
                f"https://{host}:8443/Marti/api/user-management/api/list-users",
            ],
            capture_output=True,
            timeout=4,
            check=True,
        )
        response = json.loads(result.stdout)
        if not isinstance(response, (dict, list)):
            raise ValueError("Unexpected response")
    except (subprocess.SubprocessError, ValueError) as failure:
        raise RuntimeError("Authenticated messaging read failed") from failure


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile", choices=("config", "messaging", "api", "retention", "pm")
    )
    try:
        check(parser.parse_args().profile)
    except (RuntimeError, OSError, ValueError, KeyError) as failure:
        parser.exit(1, f"TAK is not ready: {failure}\n")
