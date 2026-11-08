# Physical SM-P900 pair preflight — BOOT confirmed, Mali visibility incomplete (2026-11-07)

## Source: actual TWRP report supplied by device owner

A small read-only device report `elharika-r15-matched-pair-preflight.txt` contains:
- `device=v1awifi`, `bootloader_family=P900`.
- `boot_status=CURRENT_R7P0_KBUILD_FIXED`.
- `boot_r7_prefix_sha256=f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0`, **exactly matching** the 5,437,456-byte experimental Kbuild-fixed r7p0 boot image from GitHub run `42272497938`.
- `boot_r15_prefix_sha256=25402ca83d882ae1ed2d506690ec0c0abe561b89428b44ad7654571c3fde2569`: **not** the archived original r15p0 BOOT SHA. This extra-length prefix of the current r7 image is NOT a malfunction.
- `mali_status=NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY`, `mali_path=`, `mali_sha256=NOT_VISIBLE`. Thus **the current physically installed Mali EGL binary is not yet identified**, even though previous Android crash reports strongly suggest UK10 before recent changes.
- `boot_partition_modified=NO`, `system_partition_modified=NO`, `data_partition_modified=NO`, `flash_approved=NO`.

**Interpretation:** The read-only device BOOT fingerprint is conclusive. The missing Mali path is **not** proof that its binary is absent/corrupt. Possibilities: System was not mounted in recovery; installed EGL library is under a different mountpoint/path; `/system/vendor` symlink was excluded by the initial tool. A new flash is **not warranted**.

## Non-destructive correction to diagnostics

Added `diagnostics/twrp-mali-system-paths-readonly-v2.sh` as a **System mount + symlink-aware Mali discovery** tool, rather than repeating BOOT reads. It:
- never mounts, reboots, flashes, writes to BOOT/SYSTEM/DATA or changes libraries;
- prints whether a known TWRP System/vendor mount is present and its ro/rw flags;
- probes normal `/system`, `/system_root`, `/vendor`, and `/mnt/system` locations for `libGLES_mali.so`, safely resolving existing symlinks;
- calculates SHA-256 of a visible candidate and recognizes the pinned old UK5, tested r7/UK10 and donor r15 versions;
- writes a checksum-verified **new** TXT to microSD without overwriting previous reports.

[GitHub Actions build #42383919197](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42383919197) **SUCCESS**: ZIP/test suite and packaging passed, artifact ID `13578558146`, inner ZIP `ELHARIKA-SM-P900-MALI-SYSTEM-PATHS-READONLY-V2-TWRP.zip`. ZIP CRC was also verified after extraction. Physical TWRP execution **not yet tested**.

## Next safe step

Mount **Micro SDCard** and **System read-only** in TWRP, use the above diagnostic ZIP, then inspect `elharika-mali-paths-report.txt` (or numbered variant). **Do not Wipe, RESTORE, reflash BOOT or install any full system.img** until exact on-device Mali path/SHA and complete rollback requirements are reviewed. The existing r15p0 donor static linker audit passing is insufficient for release approval.

PR #7 stays draft; main unchanged.

## Later physical confirmation — installed Mali ELF found and verified

The user navigated physical TWRP File Manager to `/system/vendor/lib/egl/`, showed the existing `libGLES_mali.so`, then ran `sha256sum /system/vendor/lib/egl/libGLES_mali.so` in recovery Terminal. The displayed SHA256 is **`34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde`**, an exact match for the pinned, previously tested **UK10 EGL library**.

Together with the prior independent BOOT SHA, this conclusively identifies the **physically installed test pair**:
- **Kernel BOOT:** r7p0 Kbuild-fixed experimental BOOT, SHA256 `f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0`.
- **Userspace EGL:** UK10 Mali `libGLES_mali.so`, SHA256 `34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde`.
- **Hardware:** GPU detection and `/dev/mali0` were seen in prior logs, but five native BootAnimation SIGSEGVs still show the EGL frame swap path is broken. The current screen remains black.

The earlier `NOT_VISIBLE` reports were limitations of the diagnostics' System mount/path detection, **not proof that the library was absent**. Stop repeating this TWRP hash collection: the installed pair is now known.

**Engineering gate:** A candidate pairing of an actual r15p0 BOOT with source-verified `U:r15p0-00rel0` donor Mali EGL has passed static ELF dependency closure, but has **not** proven a successful UK ioctl handshake or actual surface presentation. Before offering any installer, obtain exact original BOOT and existing installed EGL backups, a recovery-restorable path for both, and a narrowly scoped reversible matched-pair update; never flash only the Mali ELF on the current r7p0 BOOT. Do not treat this identity confirmation as a working ROM or approve any flash. PR draft remains unmerged.
