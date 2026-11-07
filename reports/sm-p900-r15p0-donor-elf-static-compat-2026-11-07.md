# SM-P900: verified r15p0 donor Mali on Android 11 source image (2026-11-07)

**State: static linker integration candidate identified, no repaired hardware boot or authorized flash.**

## Earlier verified blockers

The physical SM-P900 has a black screen. The original r15p0 / stock-origin Mali ELF (system SHA256 `3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433`) requests UK5.1 and cannot initialize the pinned r15p0 kernel's UK6–UK10 handshake; this was proven in `reports/mali-uk5-blocker-2026-11-06.json`. The r7p0 kernel Kbuild repair restored GPU probe and `/dev/mali0`, but with a custom UK10 ELF it still crashes on Mali buffer swap, with five physically captured native tombstones (reported `#00 PC 0x00263458`). Reflashing the same r7p0 boot or the unchanged UK5 system will not fix the issue.

## New, pin-verified same-model donor evidence

- Vendor source: `salih4187/android_vendor_samsung_universal5420-common@8f5241f7637477d3ecae65c67b9315d343257fad`; proprietary ELF Git blob SHA1 `860898a5a59142f9917dcad28f5e05a9796d03b2`.
- Original donor `libGLES_mali.so`: 26,858,432 bytes, SHA256 `a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839`; BuildId `541f48d27481c7fc59e3b9ebd6929c33`. **Distinct** from the blocked UK5 binary, tested UK10 binary and Samsung original stock binary.
- **DDK release banner from the proprietary ELF itself: `U:r15p0-00rel0`.** Independently, exact-device `salih4187/android_kernel_samsung_exynos5420@35d960ed3c2de3d5558b782257053599cded659e` defconfig selects `CONFIG_MALI_T6XX_R15P0=y`. Matching DDK family supports a coherent donor candidate, but **does not prove the UK ioctl handshake or live GPU operation**.
- Static exact-UK5.1 handshake site from the previously proven bad ELF does not occur in donor source. Nor does the donor contain the exact multi-instruction UK10.0 call-site from the separate known UK10 candidate. **Neither absence establishes the donor's actual runtime UK API request**. See [pinned UK10 callsite comparator #42380470605](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42380470605).
- [Donor DDK/ELF provenance #42380767002](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42380767002) verified original SHA, BuildId, DDK version and dynamic dependencies.
- The publicly advertised 805 MB /e/OS Android 11 OTA was **not validated**: [download #42377722674](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42377722674) canceled after ~30 MB at ~67 KB/s. Don't claim that donor public ROM's full boot/system combination is verified. Further large automatic downloads disabled.

## Measured static integration against our EXACT prior Android 11 system

[GitHub ELF closure run #42381213655](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42381213655) **SUCCESS**. Read-only input: built Android 11 `system.img`, SHA256 `a0e5904b2bb20bfb350090bef50e465514a482d71c67870a86d9711ebdc03ead` from run #42289790703 (touch HAL source corrected but still has wrong UK5 installed). Expanded exact 2,299,998,208-byte ext4 image, no compiler/build.

- Audited donor r15p0 proprietary ELF **and both exact Exynos5 board modules**, `gralloc.exynos5.so` SHA256 `aa207149efd396b18951487f9cb7e1cdab52c38127f9b8fd7958c12de45a6dfe`, `hwcomposer.exynos5.so` SHA256 `ddbab3e50c62dec5f8b53110352ec2c5f1fc6485483d3d6847fb74f38105857a`.
- Checked **63 dependent shared libraries**, **zero missing libraries**, **zero unresolved strong imported symbols**. Driver does **not** require text relocations. Verified ELF references include `libion.so`, `libstdc++.so`, `libc++.so`, `libui.so`, `libbinder.so`, `libhardware.so`.
- Source image bytes unchanged; donor proprietary binary downloaded only transiently in GitHub runner and deleted; report uploaded as **metadata only** (artifact ID 13577906587).
- This proves *static symbol closure against the tested image*, **not** Android runtime linker namespaces, dlopen paths, Gralloc native handle ABI, ION ioctl semantics, HWC connection, physical EGL buffer swap or visible launcher. No flash authorization and no deployable ROM created.

## Controlled next engineering gate (NOT YET FLASH APPROVED)

1. Prepare a **coherent** trial of original r15p0 kernel and pinned donor r15p0 userspace with the already-built Android 11 system; preserve exact SHA validation and TWRP restore of both boot and original EGL library. The current tablet reportedly runs **r7p0**; copying the donor library alone into this kernel is expressly forbidden.
2. Ensure exact original r15p0 BOOT image SHA `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14` can be recovered from a verified artifact or rebuilt and checked; the newly downloaded r7p0 artifact is **NOT** the correct r15p0 boot. Do not infer a safe rollback from a filename. Preflight full BOOT partition and existing installed Mali SHA before touching them.
3. Audit donor proprietary ELF load namespaces and actual kernel UK handshake using a restricted on-device diagnostic; no guessy ARM binary hot-patches.
4. Require physical `eglSwapBuffers` frame presentation, launcher and Wacom S Pen input before any real ROM release. If test fails, collect native crash evidence and rollback without wiping Data.

**Practical result:** For the first time in this bring-up series we have a pinned donor r15p0 Mali shared library with a matching DDK-family kernel source and **no static library-link blockers** on the Android11 system image. It is a viable engineering lead, **not yet a working or install-ready ROM**.
