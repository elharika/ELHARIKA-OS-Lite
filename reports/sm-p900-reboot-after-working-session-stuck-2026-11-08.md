# SM-P900: previously working Android becomes stuck at boot animation after power-off

Date: 2026-11-08

## Observed on the physical tablet

User reports ELHARIKA OS Lite was functioning, then after tablet powered off, the next power-on remained on the Android-style blue gradient / cyan moving-stroke boot screen. Screenshot shows the stock-style boot animation (not the experimental custom Black Ice wordmark), so identifying this solely as a Black Ice animation bug would be unwarranted.

Device-specific earlier evidence shows the r15p0 BOOT + matching Mali shared library previously rendered the installed launcher successfully, but screenshots of `/data/system/dropbox` subsequently contained numerous `system_server_watchdog` reports and `system_app_native_crash` reports. This is consistent with intermittent framework instability but **does not prove which service is now blocking the second boot**. Exact current ROM package, shutdown reason and boot completion duration have not been confirmed. Never infer that all subsystems passed QA based on one initial UI screenshot.

## First no-reflash recovery trial for the owner

1. Charge over 50%, especially if tablet powered off unexpectedly.
2. TWRP > Wipe > Advanced Wipe: select ONLY `Dalvik / ART Cache` and `Cache`; do NOT check `Data`, `System`, `Internal Storage` or `Micro SDCard`.
3. Reboot system; on this developer profile `WITH_DEXPREOPT := false`, ART may have to regenerate compilations. Allow one complete startup attempt.
4. This is a non-destructive diagnostic trial, **not a verified root-cause fix**. If still at boot animation, don't repeat full ROM flashing or wipe Data blindly.

## Least-complex evidence collection if cache regeneration does not help

TWRP > Mount (ensure Data is accessible; microSD mounted), Advanced > Terminal:
```
tar -czf /external_sd/ELHARIKA-boot-reports.tgz -C /data/system dropbox
```
This copies the existing DropBox reports to a **single microSD file**, not to System. The user can share this one archive to identify the actual processes and timestamps, subject to reviewing its potentially sensitive contents.

If Android ADB is available while animated, the live `getprop sys.boot_completed`, `getprop service.bootanim.exit` and `logcat -d -b all` distinguish framework readiness from an animation-only stuck UI. Never substitute TWRP's `getprop` for Android runtime properties.

**No new ROM flash is approved; don't erase Data without identifying the origin of the cold-boot regression.**
