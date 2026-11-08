# SM-P900: R7 UK10 verified backup plus R15 donor staged pair (Nov 7, 2026)

**Result:** GitHub produced two independent artifacts without rebuilding Android, touching the tablet, or issuing flash approval.

## Current observed physical state (confirmed, not assumed)
- SM-P900 / v1awifi BOOT: `r7p0`, SHA256 over 5,437,456-byte image prefix `f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0`.
- Mali ELF at `/system/vendor/lib/egl/libGLES_mali.so`, SHA256 `34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde` = `UK10`.
- Android still black screen with physical BootAnimation EGL swap SIGSEGV. Don't reflash this known-failing pair.

## Artifact A — pre-trial **BACKUP ONLY**

[Build #42386188728](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42386188728) **SUCCESS**; artifact `13578834387`; inner `ELHARIKA-SM-P900-R7P0-UK10-VERIFIED-BACKUP-ONLY-TWRP.zip`, **3,400 bytes**, SHA256 `49d1b49bd019b22f5e0c35dfeee623c29dcabdd01cd85df30ebfb1d6359edb08`.

When intentionally run inside physical TWRP, this ZIP **only reads** 8 MiB BOOT and the old 27MB Mali ELF, verifies both exact source fingerprints, copies them into a **new** microSD folder, rechecks both, and writes `VERIFIED_BACKUP.txt`. No system/boot/data writes, no ZIP installer of Android components, no auto-reboot. Requires TWRP System mounted read-only, microSD mounted, at least 128 MiB available, validated P900 bootloader, exact current BOOT/ELF bytes.

Binary backup outputs are retained exclusively on the user's microSD, not on GitHub. Small TXT report can be uploaded for next proof gate. If power fails during writing, hidden staging directory remains **unverified**; only final folder with marker is a completed backup. Independently restoring the backup is NOT yet tested.

[Backup report verifier](https://github.com/elharika/ELHARIKA-OS-Lite/blob/diagnostics/mali-r7p0-matched-boot-trial/scripts/validate_sm_p900_backup_report.py) rejects wrong/missing/duplicate values and never grants flash approval. [Protected regression suite #42386471030](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42386471030) **SUCCESS**.

## Artifact B — r15p0 **STAGED ONLY**, NOT INSTALLABLE

[Build #42386683022](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42386683022) **SUCCESS**; artifact `13579952234`, 17,502,709 bytes zipped. Contains:
- Exact previous Android 11 experimental `r15p0` BOOT: 5,462,032 bytes, SHA256 `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14`.
- Donor SM-P900 Mali userspace ELF: 26,858,432 bytes, SHA256 `a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839`, GNU BuildId `541f48d27481c7fc59e3b9ebd6929c33`, proprietary DDK banner `U:r15p0-00rel0`.
- Strict `manifest.json` and DO-NOT-FLASH README. ZIP **intentionally has no TWRP update-binary, no updater-script and no system.img**. It is not a ROM and must NOT be flashed.

Prior [ELF dependency closure #42381213655](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42381213655) found 0 missing shared libraries and 0 unresolved strong symbols among 63 libraries. This is NOT proof of successful UK ioctl negotiation, EGL swap, visible launcher or Wacom pen.

## Next engineering gate before any real flash

1. Device owner executes the small pre-trial BACKUP ZIP once, retains full two binary files in its new microSD directory and supplies only `VERIFIED_BACKUP.txt`. Read-only backup may fail if model, current BOOT/Mali bytes, free space, or microSD mounting are different; on fail nothing should be flashed.
2. Review checksums and create/rehearse exact **rollback of BOTH BOOT and original Mali**, with original inode attributes preserved. Previous generic Restore attempts have been problematic, so this is essential.
3. Only after these proofs, build a narrowly scoped *paired* R15 experiment TWRP installer gated by the verified backup location, exact current bytes, exact candidate bytes, device model/partition mapping and explicit experimental consent. Never install r15 ELF alone over r7 BOOT or the known UK5-mismatched system image.
4. In vivo check GPU initialization, EGL frame swap, launcher display, and Wacom. The existing system remains experimental until these work.

**No new experimental ROM has been flashed; no successful physical Android boot established. Main unchanged; PR #7 draft.**
