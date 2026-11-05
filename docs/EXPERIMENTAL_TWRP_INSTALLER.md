# SM-P900 experimental first-boot installer

This is a development candidate, not an approved release. Boot, touchscreen, GPU,
Wi-Fi, Bluetooth and S Pen have **not** been tested on a physical tablet. Camera
and GPS packages are disabled because the stock binaries have incompatible APIs.
The inherited kernel command line requests **SELinux permissive**; this and the
userdebug/testkeys build must be resolved before production approval. Do not use
sensitive data or accounts. Wacom G9PLL is enabled in the actual embedded kernel
configuration; this is compile-time evidence only, not a pen operation test.

## Inputs

- System: successful run 41862679569, sparse SHA-256
  `fd145e39215b7839d3a414a23a58bcd7cec2707b551e409fecd2b8c44b663f61`.
- Boot: successful run 42067803567, SHA-256
  `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14`.
- Both builds have identical project revision maps in their platform locks.
- Full raw ext4 filesystem is checked using read-only `e2fsck -fn` before packaging.
- Kernel config extracted from the actual LZMA-compressed kernel confirms
  `CONFIG_V1A_WIFI=y`, `CONFIG_INPUT_WACOM=y`, `CONFIG_EPEN_WACOM_G9PLL=y`,
  `CONFIG_RD_XZ=y`, `CONFIG_XZ_DEC=y`, and 64-bit Binder IPC ABI.

## Before installation

1. Verify **SM-P900** in Download Mode; no other variant is supported. Preserve a
   matching stock firmware package and a means to restore it using Download Mode.
2. Use recovery built specifically for SM-P900/v1awifi. Back up Boot, System, Data
   and EFS to external storage if those partitions still contain useful data.
   A backup after wiping cannot recover previously erased files.
3. Download the GitHub Actions artifact, then extract the **outer download ZIP**.
   The file to install is **ELHARIKA-OS-Lite-11-SM-P900-EXPERIMENTAL-TWRP-r2.zip**.
   Do not extract that inner installer ZIP and do not flash the older development
   image artifact. Verify the inner ZIP against the accompanying `.sha256` file.
4. Copy the installer to removable microSD, mounted by TWRP at `/external_sd` or
   `/external_sdcard`. Leave **2.5 GB additional free space** for image extraction.
5. In TWRP Mount, uncheck System. Keep sufficient battery charge and stable power.
   Do not change the partition table or wipe any additional partitions to resolve
   an installer preflight failure. If Data has already been wiped, do not wipe it
   again. Migration from an existing ROM is untested.

## Installation and diagnostics

Use TWRP **Install**, selecting the inner installer ZIP. The shell installer
requires `ro.product.device=v1awifi` and a `P900` bootloader identifier. It checks
the expected named block-device mappings, an 8 MiB Boot partition, adequate System
capacity, absence of mounted targets, image lengths, CRC extraction and SHA-256.
It writes System, verifies its readback, then writes Boot and verifies readback.
It does not write Data, EFS, Recovery, the bootloader, PIT or any other partitions.

These checks cannot prove bootability or hardware operation. The recovery shell
installer itself is not yet hardware-tested. A failed write can leave an
unbootable System or Boot, so the recovery and stock restore route must be kept.
If installation fails, remain in TWRP and save `/tmp/recovery.log` to microSD
using Advanced / Copy Log, or `adb pull /tmp/recovery.log` from a connected host.
Do not bypass model, hash or capacity checks.

After verified installation, the first boot is an experiment. If the device
loops or hangs, return to recovery and collect `/proc/last_kmsg` if present along
with recovery logs; restore a known compatible backup or exact SM-P900 stock
firmware. Do not flash another model's bootloader or PIT. Runtime tests must cover
boot/reboot, sleep/wake, graphics, touch, pen pressure/hover/button/orientation,
Wi-Fi, audio, Bluetooth, storage and APK installation before acceptance.

## Installer revision 2

The user-reported SYSTEM capacity is 2,491,416,576 bytes, larger than the
2,299,998,208-byte image. Revision 1 nevertheless refused this size. Its shell
integer comparisons can overflow in a 32-bit recovery, especially at the 4 GiB
upper bound. Revision 2 uses validated decimal AWK comparisons, preserves the
minimum/maximum bounds, and prints actual and required sizes. Boundary tests
include the reported capacity, exact fit, one byte short, malformed values and
4 GiB limits. This is a packaging fix; System and Boot image hashes are unchanged.
No repartition, resize or extra wipe is required for this correction. Physical
installation and boot still require on-device testing; keep recovery logs.
