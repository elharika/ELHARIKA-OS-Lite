# ELHARIKA OS Lite — SM-P900 / v1awifi

Android 11 development project for the Samsung Galaxy Note Pro 12.2 Wi-Fi **SM-P900 only**. This is not an approved or hardware-validated release.

## Verified software work

- Full Android 11 system image built successfully in [run 41862679569](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/41862679569). Expanded ext4 filesystem passed read-only e2fsck, exit 0.
- Matching boot image built successfully in [run 42067803567](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42067803567). Boot and system project revision maps are identical.
- Custom launcher and Pen Tools source, vendor integration tools, pinned device/kernel sources, build workflows, and automated checks are included.
- Experimental TWRP packaging verifies pinned image hashes, filesystem consistency, first-stage mount configuration and ZIP CRC. The installer checks device identity, capacities, mounts and image hashes before writing only SYSTEM and BOOT, then verifies block readback.

## Release blockers

**Physical-device boot and all hardware operation remain untested**, including S Pen pressure/hover/button, touchscreen, GPU, Wi-Fi, Bluetooth, audio, sleep/wake and storage. Compile-time Wacom G9PLL support does not prove functioning pen input. Camera and GPS are disabled because stock Android 5 binaries have incompatible APIs. The inherited kernel command line requests **SELinux permissive**; this and userdebug/testkeys are unsuitable for a production release or sensitive data. The inherited stock build fingerprint also needs correction.

The old `system-development-NOT-FLASH-APPROVED` artifact is a container of images, **not a TWRP installer**. Never select it in Install Zip. A packaging artifact contains an inner `ELHARIKA-OS-Lite-11-SM-P900-EXPERIMENTAL-TWRP-r2.zip` and its checksum; extract the outer download container once. Do not confuse an experimental installer with hardware validation.

See [experimental installation and recovery notes](docs/EXPERIMENTAL_TWRP_INSTALLER.md), [actual matching boot review](reports/matching-boot-42067803567-review.json), [build documentation](docs/BUILD_AND_VALIDATION.md), and [source provenance](docs/SOURCE_PROVENANCE.md). Keep a compatible backup and exact SM-P900 stock restore route. No bootloader/PIT/repartition operations are part of this installer.
