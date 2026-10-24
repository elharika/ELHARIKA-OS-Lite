# Android 11 source and vendor audit — SM-P900

Status: DEVELOPMENT / NOT FLASHABLE. No full Android ROM build or physical-device test has completed.

## Completed

The hardware manifest now pins 11 source repositories to commit IDs. Samsung SLSI Exynos, Exynos5, OpenMAX and policy dependencies have been identified; the previous missing-owner guesses are no longer the current blocker. See rom/roomservice.xml.

The SM-P900 kernel CI succeeded at https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/40100855004 . Its configuration checks include Wacom and SELinux. This does not prove Android boot, pen operation, or runtime SELinux enforcement.

## Verified vendor conflicts

The exact target list at https://github.com/exynos5420/android_device_samsung_v1awifi/blob/ace582ea814b5b5593c1a25ac68ed7315ceefdc9/proprietary-files.txt names P900XXS0BRI1 as the source of unpinned target blobs.

The common list at https://github.com/exynos5420/android_device_samsung_universal5420-common/blob/b018612a7939d3a4ab8900e3d03ac1ca608546a0/proprietary-files.txt instead names:

- Default common blobs: T700XXU1CVG1.
- Mali graphics library: A800SKSS1CTJ1.
- Bluetooth firmware: T705XXU1CPK2.
- Widevine components: N935FXXS7CTJ2.
- aptX: marlin OPM1.171019.011.
- STLport: locally compiled open-source library; its classification must not be confused with foreign hardware firmware.

The user's strict requirement prohibits importing firmware intended for other models. Consequently the common list cannot be imported unchanged. These annotations establish source provenance, not that every file is incompatible: shared hardware compatibility would still require independent validation and does not override the project constraint.

The exynos5420/proprietary_vendor_samsung repository was found, but the branch search for 18.1 returned no match. Its existence is not evidence of a compatible Android 11 vendor set.

## Remaining work

The user-supplied SM-P900 P900XXS0BPL4 stock dump has now been verified and scanned. 140 distinct files were staged with matching hashes; nine requirements remain unresolved. See reports/stock-vendor-staging.json and docs/BUILD_AND_VALIDATION.md. Continue comparing ELF ABI/symbols, firmware interfaces and loader requirements against actual target platform output. Stock Android 5 blobs are NOT assumed to work on Android 11. Adapt source HALs/shims only after measuring the missing interfaces. Resolve licensing before redistributing proprietary binaries.

A stock dump supplies investigation inputs, not an automatic solution. Full platform integration, sufficient build resources, packaging and physical-device testing remain necessary. Do not add a vendor manifest entry merely to silence the readiness audit. No proprietary binaries were imported or published in this audit.
