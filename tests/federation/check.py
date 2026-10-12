"""Set up federation through REST and prove CoT and state survive TAK restarts."""

import argparse
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

NAMESPACES = ("tak-federation-a", "tak-federation-b")
GROUP = "federation-test"
CONNECTION = "federation_test"


def run(command: list[str], *, input: str | None = None) -> str:
    return subprocess.run(
        command, check=True, capture_output=True, text=True, timeout=60, input=input
    ).stdout


def fingerprint(path: Path) -> str:
    pem, end, _ = path.read_text().partition("-----END CERTIFICATE-----")
    if not end:
        raise ValueError(f"Missing certificate in {path}")
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem + end)).digest().hex(":").upper()


@dataclass
class Peer:
    namespace: str
    directory: Path
    api_port: int
    cot_port: int

    @property
    def host(self) -> str:
        return f"tak-server.{self.namespace}.svc"

    def api(
        self,
        path: str,
        method: str = "GET",
        body: dict | None = None,
        certificate: Path | None = None,
        identity: str = "tak-probe-identity",
        expected_status: int = 200,
    ) -> dict:
        command = [
            "curl",
            "--silent",
            "--show-error",
            "--noproxy",
            "*",
            "--max-time",
            "30",
            "--connect-to",
            f"{self.host}:8443:127.0.0.1:{self.api_port}",
            "--cacert",
            str(self.directory / "tak-probe-identity.ca.crt"),
            "--cert",
            str(self.directory / f"{identity}.tls.crt"),
            "--key",
            str(self.directory / f"{identity}.tls.key"),
            "--request",
            method,
            "--write-out",
            "\n%{http_code}",
        ]
        if body is not None:
            command += [
                "--header",
                "Content-Type: application/json",
                "--data-binary",
                "@-",
            ]
        if certificate is not None:
            command += [
                "--form",
                f"file=@{certificate};type=application/x-x509-ca-cert",
            ]
        command.append(f"https://{self.host}:8443/Marti/api/{path}")
        output = run(command, input=json.dumps(body) if body is not None else None)
        payload, status = output.rsplit("\n", 1)
        if int(status) != expected_status:
            raise AssertionError(
                f"{self.namespace}: {method} {path} returned HTTP {status}"
            )
        if expected_status != 200:
            return {}
        response = json.loads(payload)
        if response.get("errors") or response.get("messages"):
            raise AssertionError(f"{self.namespace}: {method} {path} reported errors")
        return response


@contextmanager
def forward(kubectl: list[str], namespace: str, directory: Path) -> Iterator[Peer]:
    with (directory / "port-forward.log").open("w+") as log:
        process = subprocess.Popen(
            [
                *kubectl,
                "-n",
                namespace,
                "port-forward",
                "pod/tak-server-0",
                ":8443",
                ":8089",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                log.seek(0)
                ports = dict(re.findall(r"127\.0\.0\.1:(\d+) -> (\d+)", log.read()))
                mapped = {int(remote): int(local) for local, remote in ports.items()}
                if 8443 in mapped and 8089 in mapped:
                    yield Peer(namespace, directory, mapped[8443], mapped[8089])
                    return
                if process.poll() is not None:
                    break
                time.sleep(0.2)
            raise TimeoutError(f"Port forwarding failed for {namespace}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def configure(left: Peer, right: Peer) -> None:
    for local, remote in ((left, right), (right, left)):
        certificate = remote.directory / "tak-cot-identity.ca.crt"
        trusted = {c["fingerPrint"] for c in local.api("federatecertificates")["data"]}
        if fingerprint(certificate) not in trusted:
            local.api("federatecertificates", "POST", certificate=certificate)
    outgoing = {
        "displayName": CONNECTION,
        "address": right.host,
        "port": 9001,
        "protocolVersion": 2,
        "enabled": True,
        "tls": True,
        "reconnectInterval": 3,
        "unlimitedRetries": True,
    }
    current = left.api(f"outgoingconnections/{CONNECTION}").get("data")
    if current is None:
        left.api("outgoingconnections", "POST", outgoing)
    elif any(
        current.get(key) != value for key, value in outgoing.items() if key != "enabled"
    ):
        raise AssertionError("Existing test connection differs from the fixture")
    elif not current["enabled"]:
        left.api(f"outgoingconnectionstatus/{CONNECTION}?newStatus=true", "POST")
    for local, remote in ((left, right), (right, left)):
        peer_id = fingerprint(remote.directory / "tak-cot-identity.tls.crt")
        deadline = time.monotonic() + 90
        while local.api(f"federatedetails/{peer_id}").get("data") is None:
            if time.monotonic() >= deadline:
                status = left.api(f"outgoingconnectionstatus/{CONNECTION}")["data"]
                raise TimeoutError(
                    f"{local.namespace} did not discover its federate: {status.get('lastError')}"
                )
            time.sleep(2)
        groups = local.api(f"federategroups/{peer_id}")["data"]
        if {(g["group"], g["direction"]) for g in groups} != {
            (GROUP, "INBOUND"),
            (GROUP, "OUTBOUND"),
        }:
            local.api(
                "federategroups",
                "POST",
                {"federateId": peer_id, "group": GROUP, "direction": "BOTH"},
            )
        local.api("federationconfig", identity="federation-client", expected_status=403)
        local.api(
            "federategroups",
            "POST",
            {"federateId": peer_id, "group": GROUP, "direction": "BOTH"},
            identity="federation-client",
            expected_status=403,
        )


def wait_connected(left: Peer, right: Peer) -> None:
    deadline = time.monotonic() + 90
    pending = [
        (local, fingerprint(remote.directory / "tak-cot-identity.tls.crt"))
        for local, remote in ((left, right), (right, left))
    ]
    while pending:
        pending = [
            (peer, peer_id)
            for peer, peer_id in pending
            if not any(
                c["federateId"] == peer_id and c["connectionStatusValue"] == "CONNECTED"
                for c in peer.api("activeconnections")["data"]
            )
        ]
        if pending:
            if time.monotonic() >= deadline:
                raise TimeoutError("Federation did not reconnect within 90 seconds")
            time.sleep(2)


def snapshot(peer: Peer, remote: Peer, kubectl: list[str]) -> dict:
    peer_id = fingerprint(remote.directory / "tak-cot-identity.tls.crt")
    certificates = peer.api("federatecertificates")["data"]
    groups = peer.api(f"federategroups/{peer_id}")["data"]
    outgoing = peer.api(f"outgoingconnections/{CONNECTION}").get("data")
    if outgoing is not None:
        outgoing.pop("connectionToken", None)
    if fingerprint(remote.directory / "tak-cot-identity.ca.crt") not in {
        c["fingerPrint"] for c in certificates
    }:
        raise AssertionError(f"{peer.namespace} does not trust the remote CA")
    if {(g["group"], g["direction"]) for g in groups} != {
        (GROUP, "INBOUND"),
        (GROUP, "OUTBOUND"),
    }:
        raise AssertionError(f"{peer.namespace} has unexpected federation groups")
    store = run(
        [
            *kubectl,
            "-n",
            peer.namespace,
            "exec",
            "tak-server-0",
            "-c",
            "config",
            "--",
            "sha256sum",
            "/opt/tak/data/certs/files/fed-truststore.jks",
        ]
    ).split()[0]
    return {
        "truststore_sha256": store,
        "certificates": sorted(c["fingerPrint"] for c in certificates),
        "groups": sorted((g["group"], g["direction"]) for g in groups),
        "peer_id": peer.api(f"federatedetails/{peer_id}")["data"]["id"],
        "outgoing": outgoing,
    }


def traffic(left: Peer, right: Peer, work: Path) -> None:
    clients = work / "clients"
    clients.mkdir(exist_ok=True)
    roots = []
    for name, peer in (("client-a", left), ("client-b", right)):
        for extension, key in (("pem", "crt"), ("key", "key")):
            (clients / f"{name}.{extension}").write_bytes(
                (peer.directory / f"federation-client.tls.{key}").read_bytes()
            )
        roots.append((peer.directory / "federation-client.ca.crt").read_bytes())
    (clients / "ca.pem").write_bytes(b"\n".join(roots))
    result = run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "check-cot.py"),
            "--cert-dir",
            str(clients),
            "--server-name",
            left.host,
            "--port",
            str(left.cot_port),
            "--peer-server-name",
            right.host,
            "--peer-port",
            str(right.cot_port),
        ]
    )
    print(result.strip(), flush=True)


def restart(kubectl: list[str], namespace: str, role: str) -> None:
    command = [*kubectl, "-n", namespace]
    before = json.loads(run([*command, "get", "pod/tak-server-0", "-o", "json"]))
    if role == "pod":
        run([*command, "delete", "pod/tak-server-0", "--wait=false"])
    else:
        run(
            [
                *command,
                "exec",
                "tak-server-0",
                "-c",
                role,
                "--",
                "sh",
                "-c",
                "kill -TERM 1",
            ]
        )
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        try:
            after = json.loads(run([*command, "get", "pod/tak-server-0", "-o", "json"]))
        except subprocess.CalledProcessError:
            time.sleep(2)
            continue
        statuses = after.get("status", {}).get("containerStatuses", [])
        if role == "pod":
            changed = before["metadata"]["uid"] != after["metadata"]["uid"]
        else:
            old = next(
                s["restartCount"]
                for s in before["status"]["containerStatuses"]
                if s["name"] == role
            )
            changed = any(
                s["name"] == role and s["restartCount"] > old for s in statuses
            )
        if changed and len(statuses) == 3 and all(s["ready"] for s in statuses):
            return
        time.sleep(2)
    raise TimeoutError(f"{namespace} did not recover after restarting {role}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    kubectl = ["kubectl", "--kubeconfig", str(args.kubeconfig.resolve())]
    work = Path(__file__).resolve().parents[2] / "outputs/federation"
    result_file = work / "result.json"
    result_file.write_text(json.dumps({"complete": False, "stages": []}) + "\n")
    for namespace in NAMESPACES:
        labels = json.loads(
            run([*kubectl, "get", "namespace", namespace, "-o", "json"])
        )["metadata"]["labels"]
        if labels.get("opendefence.io/test") != "federation":
            raise ValueError(f"Refusing unowned namespace {namespace}")
    roots = [fingerprint(work / n / "tak-cot-identity.ca.crt") for n in NAMESPACES]
    if roots[0] == roots[1]:
        raise AssertionError("Federation peers must have independent CAs")
    baseline = None
    stages = [("setup", "")] + [
        (namespace, role)
        for namespace in NAMESPACES
        for role in ("config", "messaging", "api", "pod")
    ]
    results = []
    for namespace, role in stages:
        started = time.monotonic()
        stage: dict = {"namespace": namespace, "restart": role, "status": "running"}
        results.append(stage)
        try:
            if role:
                print(f"Restarting {namespace}/{role}", flush=True)
                restart(kubectl, namespace, role)
            with ExitStack() as stack:
                left, right = [
                    stack.enter_context(forward(kubectl, n, work / n))
                    for n in NAMESPACES
                ]
                if baseline is None:
                    configure(left, right)
                current = [
                    snapshot(left, right, kubectl),
                    snapshot(right, left, kubectl),
                ]
                if baseline is not None and current != baseline:
                    raise AssertionError(
                        f"Federation state changed after {namespace}/{role}"
                    )
                wait_connected(left, right)
                traffic(left, right, work)
                baseline = current
            stage["status"] = "passed"
        except Exception as error:
            stage["status"] = "failed"
            stage["error"] = str(error)
            if isinstance(error, subprocess.CalledProcessError):
                stage["error"] += "\n" + (error.stderr or "")
            raise
        finally:
            stage["seconds"] = round(time.monotonic() - started, 2)
            result_file.write_text(
                json.dumps(
                    {
                        "complete": len(results) == len(stages)
                        and stage["status"] == "passed",
                        "stages": results,
                        "state": baseline,
                    },
                    indent=2,
                )
                + "\n"
            )
        print(
            f"PASS: {namespace}/{role or 'REST setup'}; federation state and traffic verified",
            flush=True,
        )


if __name__ == "__main__":
    main()
