# SM-P900 Android 11 donor-vs-ELHARIKA graphics baseline — 2026-11-07

**Engineering status:** read-only research; no Android/kernel build, no partition flash, no rollback requested. ELHARIKA OS Lite still has a black-screen BootAnimation SIGSEGV.

## External exact-device reference

A February 27, 2026 community ROM exists for **SM-P900 / v1awifi**: `e-2.3-r-20260227-UNOFFICIAL-v1awifi.zip`, based on /e/OS R (Android 11). This is an **unofficial** release, not verified booting on the user's specific tablet. Source: https://community.e.foundation/t/76030 (Feb 28, 2026 post).

The candidate repositories are pinned, not followed as moving branches:
- `salih4187/android_kernel_samsung_exynos5420@35d960ed3c2de3d5558b782257053599cded659e`
- `salih4187/android_device_samsung_universal5420-common@22e5a28343d78578c4d604f3f26fcc709c9435f2`
- `salih4187/android_device_samsung_v1a-common@ff8fb2eed9ff6a2a6b723c44681cf0f3344c07a9`
- `salih4187/android_vendor_samsung_universal5420-common@8f5241f7637477d3ecae65c67b9315d343257fad`

## Confirmed by pinned source inspection and CI

[Source pairing audit #42377521347](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42377521347) PASSED:
- Exact SM-P900 donor `lineageos_v1awifi_defconfig` selects `CONFIG_MALI_T6XX_R15P0=y`, with r7p0 unset. The earlier exynos5420 donor source also selected r15p0.
- The physically tested ELHARIKA candidate `boot.img` instead selected r7p0 after Kbuild repair. It probes `/dev/mali0`, but its `BootAnimation` crashes on first EGL frame submission with physical `#00 PC 0x00263458`.
- The donor `system_prop.mk` graphics properties are byte-identical to the prior exynos5420 common baseline, including `debug.hwc.winupdate=0`, `ro.surface_flinger.running_without_sync_framework=true`, and maximum three acquired buffers.
- Donor vendor tree has `proprietary/vendor/lib/egl/libGLES_mali.so` as Git blob `860898a5a59142f9917dcad28f5e05a9796d03b2` (Git SHA-1, **not** binary SHA-256). The older `exynos5420` donor tree uses the same blob object. This implies no newer Mali binary from these sources by simply switching GitHub repos.
- The donor v1a-common VINTF still advertises `IKeyDisabler` and `ITouchscreenGesture`; copying donor manifest alone won't remove the optional HAL service wait. ELHARIKA source workaround remains useful.
- Source/CI tests do not prove which exact binary versions the community-distributed ROM installs or that the ROM boots on the user's tablet.

## Read-only published reference ROM inspection

[ROM inventory workflow #42377722674](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42377722674) tests the exact published v1awifi package, reads `boot.img` magic and hashes and enumerates system payload format, but intentionally NEVER executes install commands or publishes ROM binaries. The result must be checked before any stronger compatibility claim. A downloaded source archive is not trusted solely by its filename.

## Immediate implications

1. **Do not simply flash r15p0 over an r7p0/UK10 system.** The kernel and EGL userspace must be an entire matched set; we have physical failure evidence for improvised pairings.
2. **Do not install the experimental ELHARIKA system.img** (known Mali SHA mismatch) because rebuilding it only fixed the missing optional touch HAL and still leaves the EGL crash.
3. Prioritize comparing the **actual contents of a complete reference ROM**: boot/kernel provenance, installed Mali ELF BuildId/SHA256, Gralloc, HWComposer and ION dependencies; then design a reversible matched test, not a blind proprietary ARM patch.
4. Before any release: verify physical frame swap, launcher, Wacom pen and rollback on SM-P900. Preserve current TWRP and backups. No Wipe, no RESTORE, no automatic flash approved.

**Current release state: BLOCKED_ON_REAL_GPU_FRAME_PRESENTATION.**
