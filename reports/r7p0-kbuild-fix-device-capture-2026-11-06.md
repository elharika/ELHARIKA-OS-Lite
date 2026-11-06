# SM-P900 r7p0 Kbuild fix — real hardware results — 2026-11-06 19:40 UTC

Evidence: user-provided `elharika-kbuild-fix-boot-1.tgz`. Android 11 LineageOS 18.1 / Exynos5420 / Mali-T628.

## Verified improvements
- Running kernel selects `CONFIG_MALI_T6XX_R7P0=y`, disables r15p0.
- `/dev/mali0` exists in all seven snapshots, `gpuinfo` says `Mali-T62x MP6 r0p1 0x0620`.
- SurfaceFlinger opens `/dev/mali0` and multiple GPU ioctls return success.
- `RenderEngine` initializes GLES 3.1 with renderer `Mali-T628` / vendor driver r7p0.

## Confirmed remaining problems
1. `BootAnimation` crashes with `SIGSEGV` at 19:40:43.745 UTC. Tombstone:
   `libGLES_mali.so + 0x263458` → `eglp_swap_buffers+1460` → `eglSwapBuffers`.
   Same proprietary binary offset as the earlier crash with r15p0 kernel. GPU registration alone is **not** a fix for EGL frame presentation.
2. Initial `HWComposer`: `isConnected failed for display 0: Invalid display` followed by VSYNC/disconnect notices. DisplayManager later discovers built-in 2560×1600 screen. Diagnose composer/display pipeline as distinct from GPU initialization.
3. `system_server` reaches `MakeWindowManagerServiceReady` at 19:40:52.856 and log repeatedly requests missing `vendor.lineage.touch@1.0::IKeyDisabler/default`. Current diagnostic ends at 19:41:38; no `BOOT_COMPLETED` observed. The missing service is a strong candidate for a boot-phase wait but **not yet established as the sole cause**.
4. Gralloc / bootanimation produce `ion: ioctl c0044901 failed ... Invalid argument`. This is an ION **free-handle** ioctl; do not equate it with allocation failure or assert it caused the segfault.

## Engineering plan
- **Do not rebuild/flash another kernel-only r7p0:** GPU register/probe now proven; focus on EGL `eglSwapBuffers` compatibility with Gralloc/ION/HWComposer.
- Inspect a *coherent* Mali r7p0 + Gralloc + Composer userspace stack and reproduce simple EGL window-swap before approving any system image.
- Apply existing guarded `fix_missing_keydisabler_hal.py` in a **separate matched system-image build**, validate effective staged VINTF manifest and service dependency path. Boot-only cannot update the installed manifest.
- Gather proof of Android reaching `BOOT_COMPLETED` and displaying usable UI, then test Wacom/graphics/audio/wifi.
- Preserve matching TWRP backup and rollback ZIPs. **No data wipe.**
- Existing r7p0 GitHub build succeeding does **not** imply successful UI boot.

**Status: BLOCKED ON SYSTEM / GRAPHICS STACK / PHYSICAL-DEVICE QA. Not a release.**
