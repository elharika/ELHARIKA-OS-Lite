# ELHARIKA OS Lite SM-P900 — next hardware evidence gate (2026-11-07)

## Confirmed before this change

- Physical tablet boots Android processes but displays a black screen. The r7p0 kernel now discovers Mali-T628 and /dev/mali0.
- BootAnimation crashes inside the UK10 Mali GLES binary at eglp_swap_buffers+1460, PC 0x00263458.
- Exact-hash ARM disassembly of the UK10 candidate found instruction `ldr r1, [r1, r8, lsl #4]`; immediately before it, `sub r8, r3, #1`. This is an indexed read with a stride of 16 bytes and a possible zero-count underflow, **not yet a proven actual zero count**.
- Board-specific gralloc.exynos5 and hwcomposer.exynos5 binaries are present. A valid system image containing an older (UK5) Mali binary remains **unsafe to flash** over the tested r7p0 BOOT.

## Actual changes in this phase

1. `diagnostics/twrp-export-existing-egl-tombstones.sh`: a read-only TWRP installer-style shell command. It validates SM-P900 model and bootloader, requires Data and microSD already mounted by the user, reads only human-readable tombstone text matching BootAnimation + eglp_swap_buffers, skips binary .pb files, exports ONLY relevant crash/PC/fault-address/register lines to a single existing-microSD destination, and refuses overwriting prior output. **Never mounts, writes to or reformats BOOT, SYSTEM or DATA; never initiates an Android boot.**
2. `scripts/build_egl_tombstone_readonly_zip.py`: packages a tiny, checksum-audited recovery utility. `tests/test_build_egl_tombstone_readonly_zip.py`: validates package structure, no mount/flash commands, executable TWRP script, and CRC.
3. `scripts/evaluate_twrp_egl_register_export.py` + regression tests: consumes exported TXT and correlates exact fault address and r1/r3/r8 against ARM indexed-read expression, including zero-element-count hypothesis. Explicitly refuses to declare a graphics or ROM fix.
4. [GitHub Actions build and tests #42357867371](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42357867371): successful; artifact ID `13568407751`, contains `ELHARIKA-SM-P900-READONLY-EGL-TOMBSTONES-TWRP.zip` and `SHA256SUMS.txt`.
5. [Full guard test suite (updated)](https://github.com/elharika/ELHARIKA-OS-Lite/actions?query=workflow%3A%22SM-P900+Mali+r7p0+guard+tests%22) includes both the read-only collector and parser tests.

## On-device action, only when the tablet is accessible

In TWRP > Mount, select Data and Micro SDCard. Extract the outer GitHub Actions artifact on a computer/phone; **install the INNER ZIP** `ELHARIKA-SM-P900-READONLY-EGL-TOMBSTONES-TWRP.zip` from TWRP. It is diagnostics only (no ROM flash). On success, upload `elharika-egl-crash-registers.txt` from microSD.

If NO_MATCHING_TOMBSTONE_FOUND, do not wipe or reboot repeatedly; Data might not be mounted/unlocked, or old reports were rotated.

## Decision gate

If the LDR effective address `(r1 + (r8<<4)) mod 2^32` matches the tombstone fault addr, and r8 == r3-1, the actual pointer/count interaction is established. If r3 == 0, empty indexed table becomes a strong candidate. Even then, root cause must be reconciled with Gralloc/native buffer ABI; **no blind NOP/ELF binary patch**, no ROM release claim.

**Hardware testing status: not completed. The exporter itself has been statically checked and GitHub-built, not run in the user's TWRP.**
