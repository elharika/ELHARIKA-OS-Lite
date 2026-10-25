# Integration review, 2026-10-25

Status: development only. No boot image, ROM, camera or stylus hardware approval.

Reviewed latest build run 40189144312: Soong preparation and the previous MobiCore duplicate were passed; Make stopped at duplicate libexynoscamera definitions. Free disk reported 25,532,825,600 bytes. This was not a disk-capacity failure.

The pinned common device camera source contains empty ExynosCameraHWImpl methods. Its library module conflicts with the verified stock libexynoscamera provider. For v1awifi only, preparation now excludes that empty library while retaining the camera HAL module. Linking against the stock library still needs actual Android compilation and ABI verification; camera operation is NOT_TESTED.

Product setup tests now provide expected environment and actual pinned Makefile fixtures. Tests evaluate Make conditionals for v1awifi and another device, verify retained libPaApi, reject changed upstream input, and check idempotence and overwrite protection. Existing ELF checks and SELinux neverallow enforcement remain enabled.

Validation completed locally: all 35 unittest cases passed; all Python scripts/tests compiled for syntax; shell scripts and 29 workflow run blocks passed bash syntax checks; ROM XML parsed. These are host tool checks, not Android hardware or full platform tests.

The build probe now runs the complete host test suite before source download. Remaining unknowns include native ABI compatibility, kernel header/toolchain compilation, SELinux policy compilation, boot ramdisk correctness, GPU operation, cameras, and S Pen interaction. These cannot be certified by static inspection.

Fixtures retain original text and attribution:
- camera.mk: exynos5420/android_device_samsung_universal5420-common, b018612a7939d3a4ab8900e3d03ac1ca608546a0, camera/Android.mk.
- mobicore.mk: exynos5420/android_hardware_samsung_slsi_exynos5420, 3058e274d99531967f68eaa1f2569616db518e3e, mobicore/daemon/Android.mk.

rom/generated-vendor contains historical rule snapshots. Active builds regenerate vendor rules with scripts/generate_vendor_rules.py from hash-verified inputs; do not use historical snapshots as the current assembly.
