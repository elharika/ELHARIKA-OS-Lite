# ELHARIKA OS Lite — SM-P900 ROM integration plan

**Status: DEVELOPMENT / NOT FLASHABLE**

Target: Samsung Galaxy Note Pro 12.2 Wi-Fi SM-P900 (codename v1awifi).
Never apply this plan to P901/P905 variants without their own device trees.

## Inputs required before a genuine ROM build

1. Android/LineageOS branch that explicitly supports this hardware and compatible Linux kernel.
2. Matching device tree and BoardConfig, including partition sizes and fstab.
3. Kernel source/configuration and boot image packaging settings.
4. Vendor proprietary firmware and HALs from a lawful source, with matching versions.
5. SELinux policy, init scripts, overlays, hardware permissions and Wi-Fi configuration.
6. Reproducible source revisions, checksums and build instructions.

## Source audit gate

Record exact git URLs, revisions, licensing and compatibility evidence for all components. Never blindly combine trees from unrelated Android versions or tablet variants.

## CI stages

- Stage 1: validate source manifest, branch, target codename and all required files.
- Stage 2: sync Android source on a provisioned build host; standard GitHub hosted runner may lack space.
- Stage 3: build and validate boot/recovery/system packaging.
- Stage 4: archive unsigned development artifacts; do NOT publish them as ready-to-flash.
- Stage 5: manually test boot, touchscreen, display, Wi-Fi, audio, mic, camera, S Pen, USB, charging, sleep/wake and encryption on SM-P900.
- Stage 6: only publish a tested, device-specific TWRP-installable release with SHA256 and recovery instructions.

## Device test checklist

| Feature | Status |
| --- | --- |
| TWRP access | User reports available; not independently verified |
| Boot to Android | Not tested |
| Touchscreen/display | Not tested |
| Wi-Fi/Bluetooth | Not tested |
| Audio/microphone | Not tested |
| S Pen | Not tested |
| Camera | Not tested |
| USB/charging | Not tested |
| Suspend/resume | Not tested |

Do not wipe TWRP or flash unrelated firmware. Do not claim a successful ROM build based on an APK build or a kernel compilation.
