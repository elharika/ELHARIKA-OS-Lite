# ELHARIKA OS Lite / SM-P900 — r15p0 matched-pair read-only gate (2026-11-07)

## Verified, not inferred

- Prior original `r15p0` BOOT from GitHub run `42067803567`, verified by *local extraction of actual artifact bytes*, is **5,462,032 bytes**, SHA256 `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14`; ZIP CRC, embedded manifest and Android BOOT magic passed. This is the original previous reference boot, not proof of successful Android UI.
- Corrected experimental `r7p0` BOOT from run `42272497938`, also verified by local artifact extraction, is **5,437,456 bytes**, SHA256 `f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0`. Real tablet earlier reported `/dev/mali0` success but Mali frame-swap crash.
- Exact pinned Android 11 same-model `r15p0` donor Mali ELF is `a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839`, DDK banner `U:r15p0-00rel0`. Offline ELF closure across 63 libraries passed in run `42381213655`; no real GPU frame swap verified.
- **On-device current BOOT + Mali SHA are not yet newly checked since previous changes.** Do not use source artifacts as an excuse to skip the user-device fingerprint.
- `main` unchanged and PR #7 remains draft.

## New no-write gate

`diagnostics/twrp-r15p0-pair-readonly-preflight.sh` is a TWRP update-binary-style diagnostic. It validates exact SM-P900 recovery and BOOT partition symlink, **only reads** the first 5,462,032 bytes of BOOT, computes independent previous-r15 and corrected-r7 prefix hashes, then (if System is already mounted read-only) calculates installed Mali library SHA256. The report is written to a *new microSD filename*, after RAM staging, checked SHA256 copy and rename; previous files are preserved. It refuses malformed device and storage identity and does not mount, wipe, reboot, flash, replace, or install any partition or library.

`scripts/evaluate_r15p0_pair_readonly_preflight.py` provides a fail-closed interpretation:
- `CURRENT_R7P0_KBUILD_FIXED + TESTED_UK10_TRIAL` -> **current failure pair confirmed, backup review only**.
- `ORIGINAL_R15P0_REFERENCE + PINNED_DONOR_R15P0` -> **matching source artifact hashes only, not proof of GPU boot**.
- Other/mixed/unknown/hidden -> **do not change installed graphics**.

[GitHub read-only preflight build and tests #42382742130](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42382742130) **SUCCESS**. Exact original and experimental BOOT artifact sizes/hashes were checked inside the runner; the TWRP ZIP CRC and manifest SHA256 passed. GitHub artifact ID `13577934310`, inner file `ELHARIKA-SM-P900-R15P0-READONLY-PAIR-PREFLIGHT-TWRP.zip`, SHA256 `6d62e2518259d84245410314aa767c1e4294f6c4bbb20b5630e9fcee79ad4681`.

[GitHub aggregate guard run #42382927336](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42382927336) **SUCCESS**, including fail-closed report classifier tests. These are emulator-independent static/shell tests; the ZIP has **not been executed in physical TWRP**.

## How to obtain physical evidence safely

1. TWRP > Mount: select Micro SDCard. To include installed Mali ELF, mount System read-only in TWRP; **never format or wipe Data**.
2. TWRP > Install the inner diagnostic ZIP `ELHARIKA-SM-P900-R15P0-READONLY-PAIR-PREFLIGHT-TWRP.zip`.
3. Upload `elharika-r15-matched-pair-preflight.txt` from microSD (or suffixed `-01.txt` if earlier output exists).
4. If `MALI_STATUS=NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY`, mount System read-only and rerun; no Android boot required.

## Exact next engineering decision

If the physical fingerprint matches the already-failed R7/UK10 pair and a verified boot/recovery rollback path is present, *then* review a **paired r15p0 boot and r15p0 donor Mali trial**, with strict precondition SHA checks for BOTH partitions, independent verified recovery backup, no data wipe, a reliable restore sequence, and explicit experimental/non-release labeling. Do not patch an ELF instruction, install the r15 Mali alone over current r7 BOOT, or flash the unfinished touch-HAL system image.

**Nothing here proves the UI boots. No experimental paired INSTALL ZIP has been published yet.**
