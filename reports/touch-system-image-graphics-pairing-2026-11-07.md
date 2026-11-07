# SM-P900 — verified system.img build and GPU pairing blocker (2026-11-07)

## Verified results, no extra Android build

- [Android 11 image build 42289790703](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42289790703) completed successfully. Sparse system.img SHA-256: a0e5904b2bb20bfb350090bef50e465514a482d71c67870a86d9711ebdc03ead; size: 949985656 bytes; expanded ext4 size: 2299998208 bytes. The system VINTF manifest no longer advertises nonexistent IKeyDisabler and retains ITouchscreenGesture.
- [Offline FS/graphics audit 42343611095](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42343611095) succeeded. The expanded image passed e2fsck -fn (five passes). The actual embedded VINTF manifest was checked. Embedded Mali and gralloc ELF headers / hashes were inspected read-only.
- [Pairing review 42343783816](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42343783816) succeeded as an audit and returned BLOCKED_SYSTEM_GPU_MISMATCH.
- **GPU userspace mismatch:** built image Mali sha256=3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433, versus r7p0 / UK10 userland last tested on the actual SM-P900 sha256=34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde.
- The built Mali library needs libm.so and existing compatibility shims and contains EGL_KHR_surfaceless_context; version-needed ELF libraries list is empty. Built gralloc.default.so sha256=50c2fde508a5b4121abeee6b78cc029004c250e84fa060b6b80cf5acc40a62c9.
- The last physically tested *paired* UK10/r7p0 configuration still crashed at eglSwapBuffers in libGLES_mali.so. Simply repacking the latest system with the paired library is NOT a demonstrated solution.

## Consequences

The new system image is structurally valid, but **not compatible with the currently tested GPU pairing**. Do not flash it and do not wipe /data or reflash BOOT. No new ROM has been flash approved. The IKeyDisabler fix is independent and remains needed in a future coherent image/update.

## Next root-cause analysis

Focus on the exact eglp_swap_buffers+1460 tombstone, HWC/Gralloc native buffer handle ABI, ION allocations/frees, correct EGL dependencies and legacy extensions. Source material: lraty-li/exynos5420-android10-compat docs/proprietary-blob-reproduction.md for a different Exynos5420 tablet; apply nothing from another device without a strict hash-pinned validation.

Safest path: verify complete EGL/Gralloc/HWC matching userspace, then devise a reversible targeted update and physically test on SM-P900. Avoid repeatedly rebuilding Android system.img for unverified guesses.

## Release gates

The presence of /dev/mali0 and successful SurfaceFlinger GLES initialization are insufficient. Require successful on-device eglSwapBuffers, visible launcher, no blocking IKeyDisabler wait, tested TWRP recovery and Wacom S Pen operation before any release approval.
