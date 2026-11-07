# SM-P900 graphics bring-up: EGL swap crash compatibility baseline (2026-11-06)

**State:** Diagnostic research only. Do not flash unverified binaries or claim Android boot based on linked GPU symbols.

## Device evidence

Latest physical SM-P900 capture: `elharika-kbuild-fix-boot-1.tgz`, analysis in `reports/r7p0-kbuild-fix-device-capture-2026-11-06.md`.

- r7p0 kernel and `/dev/mali0` are alive. SurfaceFlinger / RenderEngine sees Mali-T628 OpenGL ES 3.1.
- The first BootAnimation `eglSwapBuffers` segfaults in the proprietary `libGLES_mali.so` at build-id `1b2949cf031b30f20a970c511925875d`, `eglp_swap_buffers+1460`, and `pc 0x00263458`.
- BootAnimation reports that Gralloc4/Gralloc3 mapper interfaces are unsupported before the crash; this alone is **not** proof of an error because older mapper interfaces may be used.
- A nearby `ion: ioctl c0044901 ... EINVAL` concerns ION handle **free**, not necessarily memory allocation.
- `HWComposer` initially reports `isConnected failed for display 0: Invalid display`; framework later discovers 2560×1600 panel.

## Reusable upstream work identified (source-first)

1. Exynos5420 public common device tree for LineageOS 18.1: `exynos5420/android_device_samsung_universal5420-common`; graphics rules include `BOARD_USES_EXYNOS5_COMMON_GRALLOC := true`. The maintained `exynos5420` device family source lists its own `libGLES_mali.so` in `proprietary-files.txt`. **Do not assume** different Mali binaries match this SM-P900 kernel or Samsung vendor HALs without auditing.
   - https://github.com/exynos5420/android_device_samsung_universal5420-common
2. A separate Android 10 Exynos5420 bring-up, `lraty-li/exynos5420-android10-compat`, documents two exact legacy EGL compatibility adjustments: suppress `EGL_KHR_surfaceless_context` in favor of a dummy extension name and use a version-correct `libw.so` (legacy math ABI) instead of an incompatible public `libm.so`. The working documentation emphasizes that a naive `patchelf` operation can corrupt the ELF VERNEED filename even while DT_NEEDED looks correct. This is **not** proven to fix this Android 11 binary; it provides a concrete audit hypothesis.
   - https://github.com/lraty-li/exynos5420-android10-compat/blob/lineage-17.1/docs/bringup-root-causes.md
   - https://github.com/lraty-li/exynos5420-android10-compat/blob/lineage-17.1/docs/proprietary-blob-reproduction.md
3. Original Exynos5420 LineageOS 18.1 tablet builds exist for other devices, e.g. chagallwifi, but the published notes acknowledge Mali graphics crashes. The existence of a ROM for another device **does not** validate a flash on SM-P900.
   - https://sourceforge.net/projects/exynos5420/files/Lineage-18.1/
4. Android documents that EGL driver discovery depends on `ro.hardware.egl`, `ro.board.platform`, and `/vendor/lib/egl`; mismatching these can silently select different binaries.
   - https://source.android.com/docs/core/graphics/implement-opengl-es

## Falsifiable gates before replacing graphics userspace

- Extract and **hash** the exact installed Mali, Gralloc, mapper, allocator, and HWComposer libraries from the diagnosed system.img. Record readelf `DT_NEEDED`, `VERNEED`, `SONAME`, and ELF class/machine for all. Look for libw/libm inconsistencies. The present `patch_mali_compat.py` and `prepare_mali_candidate.py` verify strong-symbol closure; that does **not** establish semantic compatibility of native buffer handles.
- Compare `EGL_KHR_surfaceless_context` marker bytes of this exact binary against the known-good reference; do not patch a new blob by guessing locations.
- Record Gralloc private handle fields and ION heap IDs used by the current built HAL and the installed Mali userspace; verify a matching allocation/free path. Treat ion-free EINVAL as supporting evidence only.
- Reproduce a minimal Android native-window `eglSwapBuffers` on-device with logs/tombstones. A headless/surfaceless EGL smoke test alone is insufficient.
- Until that succeeds, block any new proprietary library injection or automatic installer.
- Current separate touch-HAL system build `42289790703` is a boot-phase fix; **it does not fix the GPU swap crash**. Also validate the effective staged system VINTF manifest and keep `ITouchscreenGesture`.

**Release gate remains:** physical SM-P900 launcher UI visible and stable, surface swaps verified, no endless service waits, S Pen working, and a tested backup/restore route. Nothing here authorizes merging to main or data wipe.
