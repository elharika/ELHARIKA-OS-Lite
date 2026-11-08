# SM-P900 — exact Mali BuildId and Exynos5 Gralloc compatibility audit (2026-11-07)

**Status:** targeted source/binary audit. No flashing, no Android or kernel rebuild, no physical repair claimed.

## 1. Mali userspace identity verified

[Exact SHA-pinned read-only ARM analysis #42373183056](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42373183056) **SUCCESS**.

- Public UK10 r7p0 source binary SHA-256 `a66179ef65c26a797b814e3d9cf0ab2b7f07e0d32c641f463820c0a0c49f1ee9`; actual deployed diagnostic binary had a **different full SHA** after compatibility edits.
- Crucially, the original source's **GNU ELF BuildId is `1b2949cf031b30f20a970c511925875d`**, exactly equal to the BuildId reported in all five *physical SM-P900* BootAnimation tombstones. Matching BuildId **supports the matched code ancestry**, but does not by itself prove every byte of the installed ELF is identical.
- Top crashing frame **#00** is at `libGLES_mali.so+0x00263458`, with indexed ARM32 memory read `ldr r1,[r1,r8,lsl #4]`. In all five tombstones the computed read address matches the reported fault address.
- Distinct caller frame **#02** is at `0x00476210`, `eglp_swap_buffers+1460`; the source instruction at `0x00476210` is a branch-with-link, consistent with a deeper call chain, **not the top fault instruction**.
- The helper accesses object `r2` (loaded from `[r0+0x0c]`) and uses `ldmib r2,{r1,r3}` before `r8=r3-1`. In five crash reports: `r1=r2+0x20`, `r3=r2+0x50`. This is pointer-like, but the field identities are unknown. **No vector layout or bad-count interpretation is proven**.

## 2. Pinned board Gralloc contract checked

[Read-only source audit #42373596854](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42373596854) **SUCCESS** against exactly pinned LineageOS Exynos source at `68b6c0f455aa865795bb3b111fb5839aa05d4bbb`.

- Actual built system has `gralloc.exynos5.so` and `hwcomposer.exynos5.so` (not just `gralloc.default.so`), as recorded by prior offline image inventory.
- Source `gralloc/Android.mk` compiles `MALI_AFBC_GRALLOC := 1` even for Exynos5420. **Compiling AFBC support does not mean AFBC is used at runtime**.
- In `gralloc/format_chooser.cpp`, `property_get("ddk.set.afbc", value, "0")` defaults to **OFF**. Buffer compression is conditional on the runtime property, size, format, and usage. Runtime value on this specific failed boot has **not** been checked.
- `include/gralloc_priv.h` declares the private buffer handle's 3 FD slots, variable active FD count, ION flag `0x20`, UMP flag `0x02`, and aligned 64-bit mapping fields. These are **static source assumptions** only; agreement with proprietary Mali's expected native buffer ABI is **unproven**.

## 3. What *not* to do

- Do **not** blindly set `ddk.set.afbc=0`: it already defaults to 0 in the pinned source unless a runtime property overrides it. First check the actual device/system properties.
- Do **not** modify the Mali indexed ARM instruction or pretend `r3` is a numeric array count: its observed values are pointer-like and five samples rule out a literal zero-count.
- Do **not** install the latest Android 11 `system.img` because its original Mali binary doesn't match the r7p0/UK10 userspace tested in the black-screen logs.
- Do **not** wipe/repartition/restore or recompile Android merely to repeat this static audit.

## 4. Next falsifiable test

Check whether system or init **actually sets** `ddk.set.afbc`; if not set, AFBC is unlikely to explain this crash. Then compare **source and compiled `private_handle_t` ABI/offsets** to the specific Mali driver's expected handle interpretation, along with Gralloc buffer allocation/ION lifetime around the first `eglSwapBuffers`. Require an exact-hash, reversible test and real GPU surface presentation before approving any patch.

**Conclusion:** The five physical crash samples and matching source BuildId establish a precise invalid indexed-read in proprietary Mali during frame presentation, but **do not prove** which upstream component supplied the wrong pointer or data.
