# SM-P900 Mali UK10 trial r1

This is an experimental, single-library repair candidate for the already installed
ELHARIKA Android 11 development ROM. It is not a full ROM or a release approval.

The shipped stock-derived Mali library requests UK ABI 5.1. The pinned r15p0 kernel
supports UK major versions 6 through 10, returning 10.6 for the unsupported major 5.
The library rejects that response and closes the GPU fd. The three device r3
traces agree with this static initialization path.

The candidate comes from `Valera1978/android_vendor_samsung_v1awifi`, commit
`4079dd66fc6955adb208a0633220f4b72faaf82d`, specifically the SM-P900 vendor tree.
It requests UK 10.0, which the pinned kernel negotiates as 10.0. It requires the
existing process-name compatibility bridge. Only DT_NEEDED is changed; executable
text stays unchanged. Static symbol-name checks are not runtime validation of
Android linker namespaces, EGL, hardware composition or application rendering.

## Prepare and package

Dependencies: Python 3, capstone 5.0.9, pyelftools 0.33, patchelf 0.19.3.0,
debugfs from e2fsprogs. The GitHub workflow pins the Python packages and both
binary sources. Preparation fails on unexpected input hashes or strong imports
without a matching symbol in the installed dependency closure.

```
python3 scripts/prepare_mali_candidate.py candidate.so system.ext4 prepared
python3 scripts/package_mali_candidate.py prepared kit
```

Original binary ownership, notices and redistribution restrictions remain
applicable; these tools grant no new rights over proprietary Samsung/ARM blobs.
The executable instruction excerpts in the audit identify interoperability
requirements rather than supplying a replacement implementation.

## Device procedure

1. Keep both INSTALL and RESTORE ZIPs on microSD. Verify SHA256SUMS.
2. Enter TWRP. Uncheck System under Mount. Keep the tablet adequately charged.
3. Install only `ELHARIKA-SM-P900-MALI-UK10-TRIAL-INSTALL-r1.zip`.
4. Photograph the result. If it failed, remain in recovery and send the exact error.
5. If successful, reboot System once. Do not wipe anything. Allow 90 seconds.
6. If the display remains black, return to TWRP. RESTORE-r1 restores only the
   exact original library, provided the installed library is the trial candidate.

The installer checks the SM-P900 bootloader, exact matching boot image prefix,
Android API/model, SurfaceFlinger and bridge hashes, existing Mali hash, payload
hashes and 32 MiB free System space. It writes only the existing Mali library
inode, preserving its SELinux label, owner and mode. No security setting is
changed. Normal write/checksum failures attempt in-process rollback and verify it.
Power loss during a write can still require reinstalling the diagnosed ROM;
this is not an atomic filesystem transaction. Never use the kit on another ROM.

If another capture is needed, mount Cache in TWRP and explicitly re-arm the
already installed r3 service before the next Android boot:

```
echo ELHARIKA-GPU-CAPTURE-v1 > /cache/elharika-gpu-capture.request
chmod 0600 /cache/elharika-gpu-capture.request
```

Old logs are appended/rotated by the existing service. Do not delete them before
inspection. No successful UI boot, GPU rendering or stylus validation is claimed.
