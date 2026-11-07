# SM-P900 r7p0 EGL swap failure — focused graphics HAL and ARM fault investigation (2026-11-07)

## No ROM or kernel rebuild used

1. [Read-only inventory #42345070923](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42345070923): successfully validated existing system.img SHA-256 a0e5904b2bb20bfb350090bef50e465514a482d71c67870a86d9711ebdc03ead. All relevant graphics HAL binaries were found without errors.
   - /system/lib/hw/gralloc.exynos5.so SHA256 aa207149efd396b18951487f9cb7e1cdab52c38127f9b8fd7958c12de45a6dfe
   - /system/lib/hw/hwcomposer.exynos5.so SHA256 ddbab3e50c62dec5f8b53110352ec2c5f1fc6485483d3d6847fb74f38105857a
   - /system/vendor/lib/egl/libGLES_mali.so SHA256 3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433 (UK5-era original — not matched to current r7p0 BOOT)
   - /system/vendor/lib/hw/gralloc.default.so SHA256 50c2fde508a5b4121abeee6b78cc029004c250e84fa060b6b80cf5acc40a62c9, not to be confused with actual board-specific gralloc.exynos5.so.
   - android.hardware.graphics.allocator@2.0-impl.so and android.hardware.graphics.mapper@2.0-impl-2.1.so are present under /system/vendor/lib/hw.
2. [HAL dependency review #42345251955](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42345251955): metadata confirms gralloc.exynos5.so uses libcutils/libion/libutils and hwcomposer.exynos5.so depends on libEGL, libGLESv1_CM, libhwcutils, libion, libexynosdisplay and Exynos libs. Static NEEDED entries alone do not prove that graphics buffer handle layout and ION semantics match the proprietary Mali userland.
3. [Pinned UK10 ARM disassembly #42345381148](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42345381148) succeeded using public Valera1978/v1awifi libGLES_mali.so pinned by SHA256 a66179ef65c26a797b814e3d9cf0ab2b7f07e0d32c641f463820c0a0c49f1ee9. The user-tested candidate has a dependency-only patch, so this same .text/code is the correct starting comparison, **but the exact deployed binary section layout should still be checked**. No binary redistributed or patched.
   - Real BootAnimation crash PC: 0x00263458 within eglp_swap_buffers (+1460).
   - Crash opcode: **ldr r1, [r1, r8, lsl #4]**.
   - Immediately before: **sub r8, r3, #1**; **add ip, r1, r8, lsl #4**. This is a 16-byte stride indexed table read using (r3-1). If r3==0, unsigned arithmetic would produce an index of -1. This is a testable possibility, **not a proven value of r3 on the device**.
   - A crash at the LDR shows invalid/unmapped read of an indexed address; cannot conclude whether r1 is stale, r3 is zero, or the object/table's capacity or layout is incompatible without actual register values and Android tombstone fault address.
   - The proprietary source had no matching public eglp_swap_buffers symbol in .symtab/.dynsym. The crash offset comes from the on-device tombstone, not a source debug build.

## Next evidence gate (before modifying any GPU library)

Read the FULL Android tombstone for the BootAnimation SIGSEGV from the *same boot*: fault address, r1, r3, r8, sp, and backtrace. Calculate effective read address (r1 + (r8 << 4)) modulo 32 bits and check it equals the reported fault address. Check any preceding Gralloc failures (allocation/import/free) and HWC events from that same process/time window.

Do not 'fix' the offset by substituting a NOP or memory-safety guard blindly; proprietary ELF instructions are opaque and ABI expectations unknown. A different CPU opcode without coherent native buffer lifecycle can corrupt memory. Recreate frame swap only after a reviewed ABI adjustment, with a rollback plan.

## Safety gates

- The GPU registration is now functional on r7p0; do not reflash BOOT simply to repeat tests.
- Do not flash the new mismatched system.img over that r7p0/UK10 trial.
- Touch IKeyDisabler service wait fix is compiled in the experimental image but needs coherent graphics pairing.
- Do not wipe /data, edit main, or declare successful screen boot until on-device EGL swap, launcher and S Pen are verified.

**STATUS: Device GPU probe repaired; frame submission blocked, no safe patch demonstrated.**
