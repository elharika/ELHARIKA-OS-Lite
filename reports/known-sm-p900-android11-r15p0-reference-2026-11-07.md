# ELHARIKA OS Lite — SM-P900 Android 11 working-source reference audit (7 November 2026)

## Why this changes the engineering direction

The user's **physical SM-P900** still black-screens with ELHARIKA Android 11. The custom `r7p0` kernel now probes Mali-T628 and exports `/dev/mali0`, but five BootAnimation native tombstones fault inside Mali EGL's swap path. Reflashing the same r7p0 Kbuild fix cannot solve that userland fault.

A separate publicly released **Android 11 (/e/OS R 2.3) build for the *same* SM-P900 (v1awifi)** is reported booting in community discussion. This is a stronger reference than borrowing from a different Exynos5420 device.

**Independent report, not verification on the owner's device:**
- https://community.e.foundation/t/unofficial-builds-samsung-galaxy-tab-s-8-4-samsung-galaxy-tab-s-10-5-samsung-galaxy-note-10-1-edition-2014-samsung-galaxy-tab-pro-10-1-samsung-galaxy-note-pro-12-2-for-eos-r-2-3/76030
- Source developer: https://github.com/salih4187

## Exact pinned public sources

- SM-P900 R15P0 kernel: `salih4187/android_kernel_samsung_exynos5420` revision `35d960ed3c2de3d5558b782257053599cded659e`
- Common device tree: `salih4187/android_device_samsung_universal5420-common` revision `22e5a28343d78578c4d604f3f26fcc709c9435f2`
- Shared vendor userland: `salih4187/android_vendor_samsung_universal5420-common` revision `8f5241f7637477d3ecae65c67b9315d343257fad`
- SM-P900 device tree: `salih4187/android_device_samsung_v1awifi` revision `77ccd95707ff46820dfd121a948d9c5a50e07c7f`
- GCC 4.9 (LineageOS 18.1): `LineageOS/android_prebuilts_gcc_linux-x86_arm_arm-linux-androideabi-4.9` revision `da10d2bd65e2c57d338fb6bb712ff522ad4e34e7`

## Verified GPU pairing differences (GitHub CI 42375734805, success)

| Feature | Last failed ELHARIKA runtime | SM-P900 published Android 11 reference |
|---|---|---|
| Kernel GPU DDK | r7p0 (kernel probe succeeded) | **r15p0**: `CONFIG_MALI_T6XX_R15P0=y`; r7p0 disabled |
| Mali EGL BuildId | `1b2949cf031b30f20a970c511925875d` | **`541f48d27481c7fc59e3b9ebd6929c33`** |
| Full library SHA-256 | `34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde` (modified UK10 r7p0) | **`a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839`** |
| Library size | See last device capture | 26,858,432 bytes |
| Gralloc HAL | gralloc.exynos5.so | gralloc.exynos5.so |
| SurfaceFlinger options | Pending installed property comparison | running_without_sync_framework=true, max_frame_buffer_acquired_buffers=3 |

The reference Mali binary is ARM32 little endian, and its dynamic dependencies include `libion.so`, `libui.so`, `libbinder.so`, and `libm.so`. ELF `VERNEED` names include libc.so, libdl.so, and libm.so. The reference **does not use the same original UK10 EGL code** as the crash; GNU BuildIds differ. This is decisive evidence to **stop attempting to repair the r7p0 binary through guessed instructions** and investigate coherent r15p0 kernel+userland instead.

The original ELHARIKA system image built earlier is **not** automatically compatible with this reference EGL+kernel. Its embedded EGL binary is a *third*, different, old UK5 blob. Do not pair kernel from one generation with another proprietary EGL binary.

## Build work in this phase

- Read-only source+binary comparator `scripts/audit_sm_p900_known_android11_reference.py` and regression tests; [comparison run #42375734805](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42375734805) **SUCCESS**.
- Separate [kernel-only reference build workflow](https://github.com/elharika/ELHARIKA-OS-Lite/actions/workflows/compile-sm-p900-reference-r15-kernel.yml) pins kernel/ARM GCC 4.9, verifies R15P0 config and compiles zImage, if build succeeds. **Does not build Android, produce a boot.img, or flash the device**. Its success is not yet evidence that the entire ROM boots.
- Reversible next steps after kernel evidence: review full EGL/Gralloc/HWC/ION userspace linkage, stage a matched and hash-locked system image/library set, back up exact original BOOT and SYSTEM, then test a known pair on the physical SM-P900. Never overwrite the currently installed experiment by mixing donor blobs without rollback.

## Other unresolved issues

- The `IKeyDisabler` HAL is still declared in published reference v1a-common VINTF; its existence in source alone does not prove the service is implemented or that the original ELHARIKA boot wait is fixed. ELHARIKA source-level mitigation remains in its own experimental system image.
- Wacom S Pen operation, actual rendered launcher, Wi-Fi, sound and stability all require real physical tests.
- Source publication/community user reports do not make a ROM flash-safe automatically.

**Current release decision: no complete working ELHARIKA ROM yet; do not flash a source-only kernel zImage or mismatched system image, do not wipe Data, and do not merge this draft PR.**
