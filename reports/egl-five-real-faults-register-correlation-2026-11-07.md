# SM-P900 — Five real BootAnimation EGL fault records, register correlation (2026-11-07)

## Evidence handling
The device owner supplied a **nonempty** text export `elharika-egl-crash-registers.txt` containing five matching native BootAnimation crashes. This report records **aggregated, non-identifying facts only**; do not commit raw tombstones or user-private crash logs.

## Precise matching evidence

- 5/5 records: process `/system/bin/bootanimation`; `signal 11 (SIGSEGV), code 1 (SEGV_MAPERR)`.
- 5/5 records: the exact faulting top frame **#00** is inside `libGLES_mali.so` at **PC `0x00263458`**; `BuildId: 1b2949cf031b30f20a970c511925875d`.
- In the same crash stack, frame **#02** is **PC `0x00476210`** symbolized `eglp_swap_buffers+1460`. The earlier shorthand treating `0x00263458` itself as `eglp_swap_buffers+1460` was imprecise. It is a helper function reached in the swap-buffers path.
- Exact-hash UK10 candidate disassembly at the top frame shows `ldr r1, [r1, r8, lsl #4]` (read) preceded by `sub r8, r3, #1`.
- For every crash: `(r1 + ((r8 << 4) mod 2^32)) mod 2^32 == reported fault addr`. 5/5 exact matches, not an approximate pattern.
- The registers exhibit a **repeated, precisely identical spacing** across all five boots: `r1 = r2 + 32`, `r3 = r1 + 48`, `r3 = r2 + 80`, `r8 = r3 - 1` modulo 2^32. These are **observed register arithmetic**, not proven structure offsets.
- `r3` was **nonzero** and pointer-like in all five samples. Thus the earlier **zero-count underflow hypothesis is not observed**. The observed value is not interpretable as a sane small array count.
- The crash is an invalid indexed-memory read (fault addr differs between restarts). This narrows the problem to incorrect pointer/index/descriptor use *inside or presented to proprietary Mali EGL*, but **does not establish the upstream cause**: Gralloc native-buffer handle ABI, corrupt data, EGL state, allocator/ION lifetime, and proprietary driver internals all remain candidates.

## Code/test changes
- `scripts/inspect_egl_fault_registers.py` now captures `r2` and computes the three register deltas while preserving the exact fault-address match checks.
- `scripts/evaluate_twrp_egl_register_export.py` aggregates matches of this pointer-like pattern across multiple crashes without asserting that `r3` is a count.
- Regression tests use **synthetic pointers**, not raw user addresses or logs. GitHub guard job verifies no flash-approved conclusions arise from static arithmetic.

## Engineering decision

**No speculative Mali binary patch.** A single NOP, rewritten index or swapping the wrong UK5 userland into the current r7p0 BOOT could hide the immediate crash while breaking other graphics or corrupting buffers. Next safe investigation: correlate this helper function's caller argument semantics with a matched r7p0-compatible Gralloc/HWC native buffer layout and compare the *deployed* Mali ELF hash / program counter mapping. On-device EGL frame swap and visible UI remain required before approving a flash.

Existing `system.img` (even with fixed `IKeyDisabler`) has a UK5/Mali userland mismatch and **must not be flashed over the tested r7p0 BOOT**. The physical tablet is still black-screened.

**No further TWRP collection is needed for the five basic register relationships above.** Keep backups; no Wipe/Restore/BOOT flash.
