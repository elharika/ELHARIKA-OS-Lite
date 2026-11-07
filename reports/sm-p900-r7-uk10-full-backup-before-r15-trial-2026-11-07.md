# SM-P900 physically confirmed R7P0 / UK10, secure dual-component backup gate — November 7, 2026

## New physical evidence, not inferred from build outputs

The SM-P900 owner proved from TWRP:
- BOOT image prefix SHA256 `f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0`, exactly matching the experimental **r7p0 Kbuild-fixed BOOT**.
- Installed Mali ELF at `/system/vendor/lib/egl/libGLES_mali.so` SHA256 **`34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde`**, exactly matching previously tested **UK10**.
- The current black-screen EGL swap SIGSEGV is associated with **this precise r7p0 + UK10 pair**. Do not repeat attempts to flash it hoping to fix the error.

## No-flash dual-component physical backup prepared

[GitHub Actions #42386188728](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42386188728): **SUCCESS**. Artifact `13578834387`, inner installer `ELHARIKA-SM-P900-R7P0-UK10-VERIFIED-BACKUP-ONLY-TWRP.zip`, SHA256 `49d1b49bd019b22f5e0c35dfeee623c29dcabdd01cd85df30ebfb1d6359edb08`; built ZIP is **3,400 bytes**, has only read-only microSD backup utility and README, no flash payload. Verified ZIP SHA256, CRC, TWRP update-binary structure and `sh -n` syntax.

**Backup script:** `diagnostics/twrp-backup-current-r7-uk10-before-r15-trial.sh`
- Fail-closed v1awifi/P900 and exact physical source BOOT + Mali SHA gate.
- Verifies BOOT partition alias, exact size **8,388,608 bytes**, and that installed Mali ELF is accessible at the user-confirmed `/system/vendor/lib/egl/libGLES_mali.so`. Requires 128 MiB free on external microSD.
- Reads entire physical BOOT partition to `BOOT.full-8MiB.backup` (not just boot.img image length), copies actual UK10 ELF to `libGLES_mali.UK10.original.backup`, verifies both SHA256 hashes, verifies BOOT image prefix again.
- Writes `VERIFIED_BACKUP.txt` only after checks and atomically renames a **new** stage folder to `/external_sd/ELHARIKA-R7P0-UK10-BACKUP-01` (or later unused index), without overwriting older backups.
- Does **not** mount/remount, write partitions, flash, reboot, wipe, restore, or alter Android. Any interrupted, hidden staging folder **is not** a verified backup.
- Device output files should remain on microSD; only the small TXT is needed to review readiness. The TXT alone cannot restore the device.
- Physical backup execution has not yet been independently verified; **do not assume successful rollback until user shows VERIFIED_BACKUP.txt**.

**Report checker:** `scripts/validate_sm_p900_backup_report.py` requires exact physical SHA identity and `backup_verified=YES`. It always returns `install_approved=False` and `rollback_tested_on_physical_device=False` because checking written files is not a real restore test.

## What remains before an R15P0 hardware experiment

The source-matched R15P0 kernel BOOT SHA `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14` was recovered/validated from run `42067803567`. Donor `U:r15p0-00rel0` Mali ELF SHA `a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839`; 63-dependency Android 11 static linker closure passed in run `42381213655`.

**Necessary explicit gates:**
1. Confirm physical backup on microSD contains BOTH binary files and matching TXT report (preferably independent re-read backup file checksums).
2. Implement/test a rollback path that can actually restore BOOT *and* the original Mali library in recovery; preserve SELinux context of existing inode when restoring.
3. Author paired R15 BOOT/R15 Mali exact-SHA experimental installer with strict two-target checks and verified rollback, never replace the ELF alone on R7 kernel, and never flash the old UK5 system image.
4. Test physical GPU frame swap, launcher visibility and Wacom, not just ELF link symbol availability. Mark failed trials as failed if black screen persists.
5. Keep GitHub PR #7 draft until there is physical evidence. **No released working ROM or flash approval yet.**

**Safety:** TWRP functional. No Wipe, Restore, Data format or new flash required merely to perform the backup.
