# SM-P900 — combined R15P0 graphics + optional touch HAL trial (2026-11-08)

**Development-only / do not flash until the actual Action succeeds and installer evidence is reviewed.**

## Why this separate branch exists

The 2026-11-08 S Pen diagnostic archive contains 7 Android system_server watchdog reports blocking in `vendor.lineage.touch@1.0::IKeyDisabler/default`. It also contains 5 SurfaceFlinger aborts at `eglQueryStringImplementationANDROID(EGL_VERSION)` and 3 BootAnimation crashes inside a previously mismatched Mali library. These are **separate** observed failures; S Pen causality remains unproven.

- Draft PR #8 modifies only the VINTF declaration in a new full Android build from `main`, which still uses the legacy older Mali userland. Do **not** flash that `system.img` on an R15P0 paired system.
- Draft PR #7 separately records the **user-reported physical first visible launcher boot** from a coherent R15P0 BOOT + R15P0 Mali pair. It also contains an **already compiled** Android 11 system image with the **Lineage SDK touch getter and VINTF fixes** from build [#42289790703](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42289790703), but that raw source image contained the older Mali ELF and was explicitly marked nonflashable.

This branch makes a **new combined experiment** by repacking that already built, touch-fixed source image with the *same* R15P0 BOOT and userspace Mali from the prior physical launcher-visibility trial, and preserving the optional ELHARIKA One UI Edition launcher. It does not compile a new Android kernel or platform.

## Strict inputs

| Input | Source run | SHA-256 |
| --- | --- | --- |
| Touch-corrected sparse Android 11 SYSTEM | 42289790703 | `a0e5904b2bb20bfb350090bef50e465514a482d71c67870a86d9711ebdc03ead` |
| R15P0 BOOT | 42067803567 | `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14` |
| R15P0 Mali EGL | same-device-family pinned vendor | `a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839` |
| ELHARIKA One UI Edition APK | 42453092239 | obtained and verified through source artifact `SHA256SUMS.txt` |

The workflow rejects incorrect source System SHA-256, BOOT SHA-256 and Mali ELF SHA-256. The source artifact additionally includes prior build CI proofs for disabling the **optional** SDK `IKeyDisabler.getService(true)` call and for removing its VINTF declaration while retaining `ITouchscreenGesture`. The repack checks these CI records and **independently parses the real mounted ext4 VINTF XML** before changing other files.

## Build procedure

Workflow: `.github/workflows/package-sm-p900-clean-r15-reinstall.yml` on branch `fix/sm-p900-r15p0-spen-touch-20261108`.

1. Pin and verify inputs; check that source build reported the actual touch SDK and VINTF modifications.
2. Expand the verified sparse image to 2,299,998,208-byte ext4; check with `e2fsck -fn`.
3. Inspect ext4-embedded vendor VINTF XML; require `ITouchscreenGesture` and absence of `IKeyDisabler`.
4. Replace only the exact prior Mali ELF payload in its inode; preserve ownership, permission bits and xattrs, verifying R15P0 SHA.
5. Install pinned One UI Edition as an additional system HOME app, without deleting ELHARIKA Launcher Lite.
6. Validate filesystem; produce exact-model/hash-gated **experimental** SYSTEM + BOOT TWRP ZIP and recheck CRC / ZIP32 / SHA.

## Release / installation blockers

No real SM-P900 S Pen or repeat-boot tests have been run on this **combined** image. Source validation, CI success and the earlier first visible launcher do **not** prove the combined image works. In particular, the Wacom IRQ and input-device interactions need observation after backup and with a known recovery route.

Do **not** flash the output until the result artifact's `verification.json`, `SHA256SUMS.txt`, and installation conditions have been reviewed. The installer writes entire SYSTEM + BOOT, which is inherently riskier than a no-write diagnostic and has no bundled full-system rollback. It **never automatically wipes Data**, but a separate Data wipe is irreversible and is **not** justified by these findings.

Do not combine BOOT and SYSTEM images from separate revisions, change Mali DDK arbitrarily, or treat passing Python tests as device acceptance. The running older generic full build #42509284766 is not the matched-pair release candidate.

## Physical acceptance sequence (only after the user knowingly authorizes a test)

1. Preflight exact model, TWRP, external microSD capacity, charge, and a reliable full recovery/restore path.
2. Test repeat boots using finger input without S Pen.
3. Collect system_server + graphics logcat / prior-boot kernel messages, check that no KeyDisabler watchdog remains.
4. With recovery available, test Wacom hover, side button and short pen input, while logging and verifying no restart.
5. Check EGL swap, SurfaceFlinger, drawing, sleep/wake, audio, Wi-Fi and memory stability.
6. Mark stable only after actual physical evidence; otherwise keep as experimental.

Status as of script authoring: **build was started; no completed hardware-validated artifact yet**.
