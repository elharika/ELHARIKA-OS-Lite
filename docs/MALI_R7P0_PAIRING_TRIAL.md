# SM-P900 / v1awifi: Mali r7p0 paired-kernel and touch HAL experiment

Status: **SOURCE CHANGES ONLY / NOT BUILT / NOT FLASH APPROVED**  
Input: 2026-11-06 `elharika-after-mali-trial(2).tgz` (SHA-256 `7f69eba597bdf7d357a3d6b813f85eee047cfa212b1d4a950c35096aa9633334`).  
System: Android 11, LineageOS 18.1, Exynos 5420, Mali-T628.

## What the device logs prove

- BootAnimation reaches a graphics window, then dies inside `libGLES_mali.so` at `eglSwapBuffers` with SIGSEGV.
- Pinned r15p0 kernel rejects a Mali UK ioctl: `Wrong syscall size (24) for 00000228`. In **r15p0** `0x228` selects `KBASE_FUNC_TLSTREAM_ACQUIRE` with a 16-byte expected structure. In **r7p0**, if the Samsung hardware-counter block is disabled (as in the captured kernel config), the same numeric ID maps to `KBASE_FUNC_UNSET_MIN_LOCK` instead. This confirms a concrete ID collision between the two DDK command tables; it does not alone prove the candidate binary's complete ABI behavior. This is an ABI mismatch, not proof that the failing call caused the segfault.
- The candidate Mali userspace reports `OpenGL ES 3.1 v1.r7p0-03rel0` after the trial. Matching its DDK **family** to the kernel's in-tree r7p0 implementation is a hypothesis worth isolating. Do not infer complete ABI compatibility from the r7p0 name or UK major number.
- The kernel `lineageos_v1awifi_defconfig` currently selects `CONFIG_MALI_T6XX_R15P0=y` even though the pinned kernel includes an r7p0 driver choice.
- In the same boot, `vendor.lineage.touch@1.0-service.samsung` **does run** and registers `ITouchscreenGesture/default`. It does **not** register `IKeyDisabler/default`. Nonetheless pinned `v1a-common/manifest.xml` advertises both. SystemServer waits repeatedly on the missing interface, which is a separate boot blocker.

## Code under this PR

1. `scripts/select_mali_r7p0.py`: exact-pinned-kernel revision check; guarded, idempotent defconfig switch to r7p0. Refuses unrecognized configurations.
2. `scripts/fix_missing_keydisabler_hal.py`: exact-pinned-device-tree revision check; removes only the unregistered optional `IKeyDisabler` manifest declaration while preserving `ITouchscreenGesture`.
3. `.github/workflows/mali-r7p0-kernel-trial.yml`: **kernel-only** boot experiment. Reuses the established development build and its locked Android sources. Applies **only** the guarded r7p0 defconfig change; builds `bootimage`; checks the final compiled `.config`; validates boot structure; publishes only `NOT-FLASH-APPROVED` artifacts with evidence. The optional touch HAL source patch is **not** applied by the boot-only workflow: it will not affect the already installed vendor manifest, which requires a separate matching system/vendor image update.
4. Two focused Python unit-test modules for selectors and invalid input rejection.

## Safety / test stages

| Stage | Current status |
|---|---|
| Capture and inspect real logs | Done |
| Inspect pinned device and kernel source | Done |
| Create guarded candidate source modifications | Done |
| Local unit tests for pure transform logic | 4 passed |
| GitHub Android/kernel build | **Not run at the time of this note; verify Actions** |
| Pair exact candidate Mali library and new boot image | **Not verified** |
| Restore/rollback path for both modified boot and Mali library | **Not device-tested** |
| Tablet EGL, boot animation, home screen and S Pen | **Not tested** |

## Before any hardware test

- Preserve current TWRP recovery, exact currently installed `boot.img`, and the UK10 trial **RESTORE-r1** ZIP with verified checksums. Do not flash or overwrite the known boot until it is saved and a tested recovery path exists.
- Check build evidence, in particular the final compiled kernel configuration, boot image SHA, recovery partition mapping, vendor graphics and HWC compatibility, and that the currently installed Mali library hash matches the intended pair.
- A kernel DDK version change is **not** a guaranteed repair and can itself cause a blank screen. Do not wipe `/data`.
- If graphics boots but Android still hangs, remember this **boot-only** experiment cannot fix the installed touch HAL manifest. Build/validate a separate matched system/vendor image before claiming the `IKeyDisabler` hang is resolved.
- Do not change SELinux from enforcing as a general repair or accept an unverified custom kernel as a release.

Source references:
- `exynos5420/android_kernel_samsung_exynos5420` commit `de0cdcf10dcca77b400f15d83c1edf4f264a0f02` (both r7p0 and r15p0 source trees)
- `exynos5420/android_device_samsung_v1a-common` commit `4ae15a9b02c6efb1ffe956ab386fce9b3606ea94`
- Existing Mali trial: `docs/MALI_UK10_TRIAL.md`.

## 2026-11-06 actual r7p0 device trial — observed failure and source fix

Captured file: `elharika-after-r7p0-boot-3.tgz` (18:18 UTC). Device runtime kernel `/proc/config.gz` **does** select `CONFIG_MALI_T6XX_R7P0=y` and disables r15p0, proving the new boot was loaded. However, `/dev/mali0` is **absent**, as verified in three real SurfaceFlinger strace sessions. EGL logs: `The DDK is not compatible with any of the Mali GPUs on the system`, then `EGL_NOT_INITIALIZED`; SurfaceFlinger repeatedly terminates on SIGABRT at `eglQueryStringImplementationANDROID(EGL_VERSION) failed`.

**Confirmed source-build omission:** Pinned `drivers/gpu/arm/t6xx/r7p0/Kbuild` contains four uses of undefined `CONFIG_MALI_R7P0` instead of `CONFIG_MALI_T6XX_R7P0`. Because `obj-$(CONFIG_*)` is blank for an undefined symbol, the main `mali_kbase.o` and platform registrations were omitted despite `.config` reporting r7p0=y. Separately, pinned `platform/exynos/Kbuild` uses `gpu_exynos$(platform_name).o`, but the platform name is `exynos`, which cannot select the included `gpu_exynos5420.c` object. This explains why the old r7p0 image created no Mali device, without claiming that any further driver ABI or hardware support is proven.

**Proposed fix (branch only):** `scripts/fix_r7p0_kbuild.py` patches all four Kbuild references and the Exynos5420 SoC selection. `scripts/check_r7p0_kernel_artifacts.py` requires actual compiled GPU objects **and** `kbase_platform_driver` in `vmlinux`; `CONFIG_MALI_T6XX_R7P0=y` alone is no longer accepted as a release gate. Pinned source preflights and unit tests passed; rebuilt kernel is tracked in [Actions #42272497938](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42272497938), status to be checked. **Do not flash the earlier failed r7p0 boot image again.**

Boot-only images will not fix the separately observed, missing optional `IKeyDisabler` vendor HAL manifest declaration. Recovery backup and real-device boot testing remain mandatory.
