# SM-P900 Android 11 experimental full clean reinstall WITH ELHARIKA One UI Edition

Date: 2026-11-08

## Exact tested offline artifact
- GitHub Actions run: https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42489493488
- Result: **SUCCESS** for build, post-copy SHA, strict payload provenance, ext4 e2fsck -fn, ZIP CRC, ZIP32-compatible members, and upload.
- Artifact: `ELHARIKA-SM-P900-ANDROID11-R15P0-FULL-CLEAN-REINSTALL-EXPERIMENTAL` (ID `13620977583`, uploaded size `508,818,726` bytes, not expired as of build date).
- Inside the downloaded outer GitHub artifact ZIP, the INNER TWRP file is `ELHARIKA-OS-Lite-SM-P900-Android11-R15P0-CLEAN-REINSTALL-EXPERIMENTAL.zip`, accompanied by `SHA256SUMS.txt`, `INSTALLATION-NOTES.txt`, `verification.json`. Only the inner TWRP ZIP should be installed by recovery.

## Contents
- Original Android 11 SM-P900/v1awifi developer `system.img` from build `41862679569` (pinned original SHA `fd145e39215b7839d3a414a23a58bcd7cec2707b551e409fecd2b8c44b663f61`), expanded as 2,299,998,208-byte ext4.
- Original R15P0 BOOT from `42067803567`, SHA `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14`.
- Exact same-family R15P0 Mali lib from pinned source, SHA `a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839`, replaces mismatched older Mali ELF in original inode, keeping owner/mode/xattrs and checked result.
- **ELHARIKA One UI Edition** as built on `42453092239`, system app `/system/app/ELHARIKAOneUI/ELHARIKAOneUI.apk`, `org.elharika.oneui`, apk ZIP CRC and pinned artifact checksum verified, attributes set to system app mode, original `ElharikaLauncherLite` package preserved as fallback. On HOME, user may need to select the desired Home app.
- Original earlier standard boot animation preserved from the old Android system. **Black Ice custom boot animation intentionally excluded**, because Android reportedly stopped at the splash screen after it was installed.
- Camera/GPS not qualified, tablet performance/S-Pen/audio/WiFi not fully hardware verified.

## Safe install conditions
1. This is an **EXPERIMENTAL** full reinstall package, **not certified stable**; no successful actual-device clean install of this artifact has been reported yet. The previous R15P0 matched pair did reach a usable-looking installed-app launcher UI on the device, which is partial evidence of feasibility but **not** proof of the new full-image install.
2. Copy the INNER TWRP ZIP (not GitHub artifact outer ZIP) to `/external_sd/`; at least ~2.5 GiB of free space must remain on SD for checked extraction. Charge to >50% and have a working TWRP.
3. TWRP > Mount: **uncheck System**. MicroSD must be accessible; TWRP > Install the inner `CLEAN-REINSTALL-EXPERIMENTAL.zip`. The installer verifies device SM-P900/v1awifi and P900 bootloader, 8 MiB BOOT partition and System capacity and guards, extracts and hashes the entire raw SYSTEM plus BOOT before writing, then verifies block readback. Do not interrupt power or remove SD.
4. No automatic wiping or formatting of Data, EFS, Recovery or Internal Storage. To perform a genuinely clean user-data install, wiping Data is a separate **irreversible user choice** that loses apps/settings and potentially personal files; do not do it blindly. A no-wipe reinstall may retain the boot issue if it is in Data.
5. If install reports any ERROR, do NOT wipe/reformat/reboot into incomplete system or force flashing. Preserve TWRP log and show the error.

## Known limitations
This artifact is a matched-pair DEVELOPMENT attempt with userdebug/testing build and incomplete hardware/security QA. A TWRP flash can fail if SD, battery, hardware or target partition capacity fails. No full-system rollback is bundled. A failed full-system write can leave a nonbootable device; the separate R7 pair RESTORE file does not restore a fully functioning OS. In particular, the user previously opted not to make a backup, which raises the recovery risk. Do not call it a proven working production ROM.

GitHub branch: `diagnostics/mali-r7p0-matched-boot-trial`; PR #7 draft, main unchanged.
