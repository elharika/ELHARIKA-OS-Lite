# SM-P900 regression: Android boot remains incomplete after restoring previous bootanimation — 2026-11-08

## Physical report
- Paired r15p0 BOOT + Mali r15p0 previously **reached the installed Android launcher** (actual device photo).
- Custom Black Ice full-screen animation was installed and then Android remained at a startup screen rather than the launcher.
- User reports restoring the earlier Android boot animation; **the older startup image reappeared, but Android still does not finish booting**.
- Thus restoring the older animation's visual content did **not** restore the previous successful boot state. The image by itself does not identify the failed service or establish an EGL regression. Do not assume changing bootanimation resolution will fix Android.
- Current exact runtime status of `system_server`, `SurfaceFlinger`, `SystemUI`, launcher, storage, and `sys.boot_completed` is UNKNOWN.

## No-write next diagnostic
Do not reflash the paired r15 kernel/Mali, run Wipe/Factory Reset, or overwrite the System image.
In TWRP, mount **Data read-only if available** and inspect the *names and modification times* in `/data/system/dropbox`. Relevant entries could include `system_server_crash`, `SYSTEM_SERVER_WATCHDOG`, `system_app_crash`, or `data_app_crash`. Check mounted Data space if needed. The presence/absence of these entries is only evidence for a next targeted investigation; it does not prove the cause.
If live Android ADB access is available while the startup animation is displayed, a read-only `adb shell getprop sys.boot_completed` and bounded `adb logcat -d -b all` would be more decisive than recovery-only properties. TWRP `getprop` measures recovery and **must not be mistaken** for the Android runtime.
If Data is not accessible in recovery, avoid formatting or changing encryption state merely to retrieve logs.

## Hypotheses (not findings)
One or more services (system_server, SystemUI/launcher, SurfaceFlinger) might be failing to complete boot, or a previously installed launcher might crash; a System mount/filling issue after the animation update is also possible. Only actual persistent logs or live Android properties can discriminate.
AOSP uses `service.bootanim.exit` from window/display boot orchestration; seeing an animation does not itself prove completed framework startup.

**Status:** NO ROOT CAUSE CONFIRMED; NO WORKING PATCH PUBLISHED. Main and working paired graphics kernel untouched.
