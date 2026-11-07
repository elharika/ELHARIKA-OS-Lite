# SM-P900 paired r15p0 experimental install and independent r7p0/UK10 restore — 2026-11-07

## User direction
The user explicitly requested continued development **without making a manual backup a prerequisite**. The approach below honors that preference while retaining an in-process automatic undo attempt and a separate matched-pair recovery ZIP. No full Android system.img was rebuilt.

## Confirmed hardware state before this build
- Real SM-P900 / v1awifi TWRP evidence: current R7P0 BOOT SHA256 over 5,437,456 bytes `f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0`.
- Installed UK10 Mali ELF SHA256 `34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde`, file at `/system/vendor/lib/egl/libGLES_mali.so`. This pair has the known BootAnimation native EGL crash and black screen.
- Matched R15 source BOOT from old workflow `42067803567`: 5,462,032 bytes, SHA `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14`. Source-verified R15 Mali donor: 26,858,432 bytes, SHA `a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839`, DDK `U:r15p0-00rel0`.
- Prior donor ELF closure: 63 shared libraries, zero missing dependencies or unresolved strong symbols. The live kernel UK ioctl compatibility and EGL swap are **not** proven.

## CI and two independent TWRP ZIPs

[GitHub Actions #42388315013](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42388315013) **SUCCESS**, artifact `13580631228`, after exact input SHA checks, packaging safety tests and ZIP member SHA/CRC review. The locally materialized artifact also passed SHA256SUMS and individual ZIP CRC checks.

- **INSTALL**: `ELHARIKA-SM-P900-R15P0-PAIRED-INSTALL-EXPERIMENTAL.zip` (~17.55 MB). Contains exactly BOOT R15 + Mali R15 and a TWRP script that requires original R7+UK10 on SM-P900 API30.
- **RESTORE**: `ELHARIKA-SM-P900-R7P0-UK10-PAIRED-RESTORE.zip` (~15.69 MB). Contains exactly the previously physically tested original R7 BOOT + UK10 Mali, with source checks allowing the known old or new boot/ELF identities. This RESTORE returns to the **previous still-black-screened system**, not a working Android OS.
- Neither is an Android ROM system.img. Both ZIPs write only two items: the BOOT partition and the existing proprietary Mali ELF inode under the installed System partition. They leave Data/EFS/Recovery/bootloader unchanged.

## Installer safeguards

- Only `ro.product.device=v1awifi`, P900 bootloader, correct BOOT/SYSTEM block mapping, BOOT capacity 8 MiB.
- Requires previously verified BOOT and Mali hashes before modification; rejects unknown/partially changed source hashes.
- Requires external microSD, at least 128 MiB available; read-only preflight payload sha256 and size; Android 11 API30/System model and pinned SurfaceFlinger hash; System unmounted by TWRP before the installer mounts it RW; at least 32 MiB free inside System.
- Requires battery at least 50% when sysfs reports it.
- Updates installed Mali ELF **in place**, preserving its inode/ownership/SELinux xattrs; writes exact BOOT image, syncs and verifies readback SHA of both.
- Uses a hidden **temporary** microSD undo snapshot of prior full 8 MiB BOOT and previous Mali inode contents only during the transaction. This is not a user-required persistent backup; it attempts to undo a write failure in the same session, then removes staging on success. A power interruption can still leave partial data.
- No manual backup is required by the installer. The independent RESTORE zip is a fallback if the R15 experiment installs but black screens and TWRP remains accessible.
- The RESTORE script refuses unknown BOOT and Mali hashes; a severely interrupted partial write may not match either and may require lower-level recovery. **The presence of a RESTORE ZIP is NOT a guarantee against bricking.**

## Physical use prerequisites and unknowns

1. Charge to >=50%. In TWRP > Mount, **uncheck System** (it must not be mounted by TWRP), but keep Micro SDCard accessible.
2. Copy BOTH extracted inner ZIPs from the downloaded GitHub artifact onto the tablet's external microSD. They are separate direct TWRP installers; do not flash the wrapper GitHub artifact ZIP.
3. TWRP > Install the `R15P0-PAIRED-INSTALL-EXPERIMENTAL.zip` file once. Capture TWRP installer output/error; don't wipe Data.
4. On a successful installer, reboot to Android only if comfortable with experimental risk. Check whether boot animation, launcher, graphics and Wacom work. **No physical result is available yet.**
5. If Android remains black and TWRP works, return to TWRP, uncheck System, use `R7P0-UK10-PAIRED-RESTORE.zip` to restore the earlier pair. That pair itself does not provide visible Android graphics.

**Release status: EXPERIMENTAL GPU BRING-UP, NOT VERIFIED / NOT WORKING ROM.** No tablet was remotely flashed. PR #7 remains draft, main unchanged. User opted out of a manual backup requirement; warning and alternative restore have been retained.
