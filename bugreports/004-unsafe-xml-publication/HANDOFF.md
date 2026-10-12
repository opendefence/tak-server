# 004: XML saves truncate live state and use the symlink path for backups

Status: open. The save sequence is established by binary inspection; the misplaced backup was observed live.
Crash-induced loss has not been reproduced.
Affected candidate: TAK `5.8-RELEASE-84`; see [environment](../ENVIRONMENT.md) and [evidence](evidence.json).

## Finding

`JAXBUtils.saveJAXifiedObject()` marshals XML to memory, copies the existing file to the supplied path plus `.backup`, and opens `FileOutputStream` on the live destination.
This truncates and rewrites the target instead of publishing a complete replacement atomically.
It follows a destination symlink when writing, but constructs the backup name from the unresolved path.

In T1, `/opt/tak/CoreConfig.xml` resolved to `/opt/tak/data/CoreConfig_config.xml` on the PVC.
The resulting `/opt/tak/CoreConfig.xml.backup` was a regular file in the container layer.
Thus the live target was persistent but this JVM backup was not.
The wrapper's separate atomic merge and backup do not change the Java save path.

Expected: readers see complete old or new XML, and the recovery copy remains on persistent storage with appropriate permissions.
Actual: the inspected sequence has a truncation window and the observed backup sits outside the persistent target directory.
Whether interruption causes data loss depends on timing and storage behavior; no such fault was injected.

Related permission observation: the live file-auth file and backup were `0644` in this image.
This is a recorded confidentiality concern, not proof of a hard-coded TAK mode. The process umask and packaging contribution need isolation.

## Effect of private role files

Private follower CoreConfigs remove their writes from the persistent owner's file.
They do not remove the truncation window when that owner saves its own authority.
The backup location is also a packaging issue: the supplied path and its backup can both resolve to persistent storage without changing TAK.
Do not require a canonical-path application patch solely to correct the tested mount/link layout.
Atomic publication remains a separate application concern. No crash loss has been reproduced.

## T2 backup placement

The native candidate first linked the root backup path to the PVC backup path.
A real admin save replaced that link with a regular container-layer file. The backup target was absent.
This disproved the link-only packaging fix; Python write-through tests did not exercise the vendor copy routine.

The external launcher now sets the public `LocalConfiguration.CONFIG_FILE` to the actual absolute role path before server startup.
The unchanged JAXB utility creates its backup beside that path.
A real admin save then created `/opt/tak/data/CoreConfig_config.xml.backup` with mode `0600`.
The root compatibility link remained intact. Private follower writes did not reach the persistent authority.
See [T2 evidence](../../docs/t2-native-layout.md) for the image and unchanged vendor checksums.
This fixes backup placement in the selected packaging. It does not fix truncating publication or prove crash durability.

## Reproduction and handoff

Use disposable files with the exact JAXB utility and a configuration object from the selected release.
Save through a symlink whose target is on a persistent volume. Record resolved target and backup location.
Inject interruption or I/O failure between truncation and completion, then validate both target and backup.
Record file modes under controlled umasks to separate application behavior from packaging defaults.

The proposed fix resolves the canonical target, writes a restricted temporary file in its directory, and atomically publishes the complete XML.
Place the backup beside the persistent authority, preserve required metadata, and define flush/durability guarantees for the supported filesystem.
Callers must receive save failures; see [005](../005-fileauth-save-errors-hidden/HANDOFF.md).
Review other callers before changing the shared utility. Do not replace a compatibility symlink with an unrelated regular file.

Acceptance requires real-file and symlink cases, persistent backup checks, restrictive permissions, complete XML during concurrent reads, and interruption/failure tests.
Offline tools and administrator saves must retain their behavior.
The application patch decision remains open. No atomic-save fix or crash-safety result is claimed.
