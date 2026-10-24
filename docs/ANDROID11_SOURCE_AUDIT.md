# Verified research status — SM-P900 / Android 11

The candidate ROM platform is LineageOS 18.1 (Android 11). These are repository candidates, **not a tested integrated build**.

## GitHub repositories found through connected GitHub

- exynos5420/android_device_samsung_v1awifi
- exynos5420/android_device_samsung_v1a-common
- exynos5420/android_device_samsung_universal5420-common
- exynos5420/android_kernel_samsung_exynos5420
- exynos5420/android_hardware_samsung_slsi_exynos5420
- LineageOS/android_hardware_samsung

All candidate sources in rom/roomservice.xml require branch/ref compatibility verification during actual repo sync.

## Unresolved dependencies

The common device tree lists Samsung SLSI Exynos, Exynos5, OpenMAX and SELinux repositories. The initially guessed `exynos5420/` locations were not accessible through the linked GitHub account and are intentionally **not** inserted as fictional URLs.

Vendor trees / proprietary binaries for v1awifi and common device families have not been integrated. Their license, origin, revisions and ABI compatibility must be verified.

## Release blocker

**NOT FLASHABLE.** Do not build a ZIP from these files or flash them. First resolve missing dependencies, perform a full Android platform build with a sufficiently provisioned host, and test on the physical SM-P900.

## Known upstream concerns

Community Exynos5420 Android 11 ports report Mali graphics driver crashes in some GPU-heavy apps and browser workloads, WPA2/WPA3 mixed-mode Wi-Fi problems, and limited DRM capability. A successful compile cannot resolve or rule out these issues.
