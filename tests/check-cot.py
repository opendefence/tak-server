"""Verify two issued clients exchange CoT through one or two TLS endpoints."""

import argparse
import socket
import ssl
import time
import uuid
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path


def event(uid: str) -> bytes:
    now = datetime.now(UTC)
    stamp = now.isoformat().replace("+00:00", "Z")
    stale = (now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    return (
        f'<event version="2.0" uid="{uid}" type="a-f-G-U-C" how="m-g" '
        f'time="{stamp}" start="{stamp}" stale="{stale}">'
        '<point lat="60" lon="25" hae="0" ce="10" le="10"/>'
        '<detail><contact callsign="TAK runtime check"/></detail></event>'
    ).encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cert-dir", type=Path, required=True)
    parser.add_argument("--server-name", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8089)
    parser.add_argument("--peer-host")
    parser.add_argument("--peer-port", type=int)
    parser.add_argument("--peer-server-name")
    args = parser.parse_args()
    with ExitStack() as stack:
        clients = []
        endpoints = (
            ("client-a", args.host, args.port, args.server_name),
            (
                "client-b",
                args.peer_host or args.host,
                args.peer_port or args.port,
                args.peer_server_name or args.server_name,
            ),
        )
        for name, host, port, server_name in endpoints:
            context = ssl.create_default_context(cafile=args.cert_dir / "ca.pem")
            context.load_cert_chain(
                args.cert_dir / f"{name}.pem", args.cert_dir / f"{name}.key"
            )
            raw = stack.enter_context(
                socket.create_connection((host, port), timeout=10)
            )
            connection = stack.enter_context(
                context.wrap_socket(raw, server_hostname=server_name)
            )
            clients.append(connection)
        for connection in clients:
            connection.sendall(event("presence-" + uuid.uuid4().hex))
        time.sleep(1)
        for sender, receiver in ((clients[0], clients[1]), (clients[1], clients[0])):
            uid = "exchange-" + uuid.uuid4().hex
            sender.sendall(event(uid))
            expected = f'uid="{uid}"'.encode()
            received = b""
            deadline = time.monotonic() + 15
            while expected not in received:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Peer did not receive authenticated CoT")
                receiver.settimeout(remaining)
                chunk = receiver.recv(65536)
                if not chunk:
                    raise RuntimeError("CoT connection closed before peer delivery")
                received += chunk
        print("PASS: two issuer-authenticated clients exchange CoT in both directions")


if __name__ == "__main__":
    main()
