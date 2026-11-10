# SM-P900 ELHARIKA OS Lite R16 — installable TWRP package

## Delivered behavior

Full Android 11 SYSTEM+BOOT TWRP ZIP using the exact latest R15P0 + Touch Fix +
One UI SYSTEM bytes and the corrected original-source Wacom isolation kernel.
Includes a separate BOOT-only TWRP rollback to the previous R15 kernel. No
manual BOOT image assembly is required.

**Hardware acceptance remains untested. This is an installable trial, not a
stable or problem-free release. Camera/GPS remain unsupported.**

## Integrity

| Payload | SHA-256 |
| --- | --- |
| Source full-ROM ZIP | 615b8a179e66305c30d8dea183206457d9e1db151cd4313a915440f24caa33f9 |
| SYSTEM, unchanged | a0a8abc0d59651ab46c3a99ee41e2181559a14316b7fde645580684f89d3ae10 |
| Corrected BOOT | a4c0773787ccd9c4d1a4da592ebf204512f882717d76d23b6cf1411fb32b3022 |
| Original rollback BOOT | 7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14 |
| R16 installable ZIP, local build | a15b6fd673d684f8b56f8bc16e542978187b1aed16348d2a954786b78ffcaaaa |
| R15 BOOT restore ZIP, local build | 4ef3b3f1fbebfb5d34b85f76e8a856129237c9b1e9464eaa834fdeb6f1c13265 |

R16 ZIP: 508,795,283 bytes. Restore ZIP: 5,458,326 bytes.
Compression implementations may yield different outer ZIP hashes across hosts;
all raw SYSTEM and BOOT payload hashes are fixed and required.

## Installer guards

- Exact SM-P900/v1awifi, P900 bootloader identity and known partition mapping.
- BOOT partition exactly 8 MiB; SYSTEM geometry checked with overflow-safe AWK.
- External microSD, at least 2.5 GiB free after copying ZIPs, battery >=50%.
- Refuse mounted target partitions; no automatic unmount or formatting.
- Extract and SHA-256 verify both payloads before writing either partition.
- Retain a verified full 8 MiB BOOT backup on microSD before the first write.
- Write and readback-verify SYSTEM, then write and readback-verify BOOT.
- Never wipe Data or write EFS, Recovery, bootloader or partition table.
- Restore ZIP changes BOOT only, accepts exact R16 or already-restored R15.
  Unknown or partially written BOOT is refused: rerun the full verified R16 ROM
  successfully first, then apply restore if needed.

There is no atomic cross-partition update. Power interruption can require
TWRP recovery and a successful full ROM reinstallation. The supplied rollback
restores the prior kernel behavior, including the prior known S Pen issue;
it is not proof that the previous ROM is fully stable.

## Validation

- **238 host regression tests passed.** Added real ZIP fixtures test exact
  SYSTEM/BOOT preservation, source/staging corruption rejection, streamed SYSTEM
  hash mismatch cleanup, executable installer mode, ZIP32 limits, backup/checksum
  ordering, BOOT-only rollback scope, and wrong-device abort before writing.
- Real full-ROM SYSTEM streamed, hashed and compared against the exact pinned
  source digest. Both delivered ZIPs passed CRC and structure checks.
- Installer shell syntax and Python compilation passed.
- Corrected kernel compile 42909955707 already succeeded; embedded source and
  config match the original, and BOOT independently reproduces with the original
  pinned mkbootimg source as recorded in PR #12.
- New reproducible packaging CI downloads the two pinned source artifacts and
  repeats the tests and package validation. No Android or kernel rebuild needed.
- No physical tablet was flashed or tested by these checks.
