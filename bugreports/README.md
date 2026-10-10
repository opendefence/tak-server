# TAK Server bug reports

Keep each TAK Server bug in its own numbered directory.
Each directory contains a handoff and sanitized evidence, including the evidence source and its limits.
Update the existing report when new evidence concerns the same defect.
Keep deployment-adapter defects in the implementation work rather than attributing them to TAK without evidence.

| Report | Finding | Evidence level |
| --- | --- | --- |
| [001](001-coreconfig-admin-edits-lost/HANDOFF.md) | Administrator edits are not saved with separate role IPs | Reproduced through the admin API and restart |
| [002](002-ignite-reconnect-stalls/HANDOFF.md) | Messaging replacement leaves remote services unavailable | Reproduced; TAK/Ignite root cause remains unresolved |
| [003](003-multiple-xml-writers/HANDOFF.md) | Shared-file packaging exposes multiple Java writers | Reclassified as deployment-specific; private-file validation pending |
| [004](004-unsafe-xml-publication/HANDOFF.md) | XML saves truncate the live target and misplace symlink backups | Binary inspection and live path observation; crash loss not reproduced |
| [005](005-fileauth-save-errors-hidden/HANDOFF.md) | File-auth save failures are suppressed | Binary inspection; fault injection pending |

All reports concern the [recorded T1 environment](ENVIRONMENT.md), dated 2026-10-10.
Reports 001, 002, 004, and 005 remain open. Report 003 is retained with its corrected classification and evidence history.
No report has been sent to an external tracker.
Recording a proposed fix does not authorize a TAK application patch.
The patch/source decision recorded in [implementation status](../docs/implementation-status.md) remains open.

For each new report, record the affected runtime, trigger, expected and actual behavior, reproduction steps, evidence, next action, and acceptance conditions.
State whether each conclusion comes from a live observation, binary inspection, or a hypothesis.
Include only the evidence needed to support the report.
Do not commit credentials, private keys, tokens, full configuration exports, kubeconfigs, binaries, or decompiled source.
Raw evidence remains under ignored `outputs/`; committed extracts must use explicit field selection and preserve provenance.
