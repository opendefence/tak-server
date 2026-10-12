"""The federation acceptance runner must fail closed on REST errors."""

import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from federation import check


class FederationTest(unittest.TestCase):
    def test_reconnect_wait_rejects_a_different_peer(self) -> None:
        peer = check.Peer("tak-federation-a", Path("credentials"), 18443, 18089)
        with (
            patch.object(check, "fingerprint", return_value="expected"),
            patch.object(check.time, "monotonic", side_effect=[0, 91]),
            patch.object(
                check.Peer,
                "api",
                return_value={
                    "data": [
                        {
                            "federateId": "unrelated",
                            "connectionStatusValue": "CONNECTED",
                        }
                    ]
                },
            ),
        ):
            with self.assertRaisesRegex(TimeoutError, "did not reconnect"):
                check.wait_connected(peer, peer)

    def test_fingerprint_uses_only_the_leaf_in_a_chain(self) -> None:
        pem = "-----BEGIN CERTIFICATE-----\nbGVhZi0x\n-----END CERTIFICATE-----\n"
        expected = hashlib.sha256(b"leaf-1").digest().hex(":").upper()
        with patch.object(Path, "read_text", return_value=pem + pem):
            self.assertEqual(check.fingerprint(Path("chain.pem")), expected)

    def test_unowned_namespace_stops_before_any_restart(self) -> None:
        with (
            patch.object(
                check.argparse.ArgumentParser,
                "parse_args",
                return_value=check.argparse.Namespace(kubeconfig=Path("unused")),
            ),
            patch.object(Path, "write_text"),
            patch.object(
                check, "run", return_value='{"metadata":{"labels":{}}}'
            ) as run,
        ):
            with self.assertRaisesRegex(ValueError, "Refusing unowned namespace"):
                check.main()
            run.assert_called_once()
            self.assertEqual(
                run.call_args.args[0][-4:],
                ["namespace", "tak-federation-a", "-o", "json"],
            )

    def test_verified_tls_and_error_responses(self) -> None:
        peer = check.Peer("tak-federation-a", Path("credentials"), 18443, 18089)
        with patch.object(check, "run", return_value='{"version":"3"}\n200') as run:
            self.assertIsNone(peer.api("outgoingconnections/test").get("data"))
            command = run.call_args.args[0]
            self.assertIn("--cacert", command)
            self.assertIn("--cert", command)
            self.assertNotIn("--insecure", command)
            self.assertEqual(
                command[-1],
                "https://tak-server.tak-federation-a.svc:8443/Marti/api/outgoingconnections/test",
            )
            for response in ("{}\n403", '{"errors":["failed"]}\n200', "not JSON\n200"):
                run.return_value = response
                with (
                    self.subTest(response=response),
                    self.assertRaises((AssertionError, json.JSONDecodeError)),
                ):
                    peer.api("federationconfig")
            run.return_value = "Forbidden\n403"
            peer.api("federationconfig", expected_status=403)

    def test_restart_requires_new_process_and_all_roles_ready(self) -> None:
        def pod(count: int, ready: bool = True) -> str:
            return json.dumps(
                {
                    "status": {
                        "containerStatuses": [
                            {"name": name, "restartCount": count, "ready": ready}
                            for name in ("config", "messaging", "api")
                        ]
                    }
                }
            )

        with (
            patch.object(
                check, "run", side_effect=[pod(0), "", pod(0), pod(1, False), pod(1)]
            ) as run,
            patch.object(check.time, "sleep"),
        ):
            check.restart(["kubectl"], "tak-federation-a", "messaging")
            self.assertEqual(run.call_count, 5)
