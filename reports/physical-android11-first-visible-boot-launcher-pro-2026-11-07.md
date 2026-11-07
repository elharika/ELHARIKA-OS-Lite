# SM-P900 ELHARIKA OS Lite — First visible Android 11 boot and Launcher Pro preview

**Date:** November 7, 2026  
**Device:** Samsung Galaxy Note Pro 12.2, SM-P900 / v1awifi

## Physical milestone

After installing exact paired original r15p0 kernel BOOT and same-family donor Mali userspace, the user observed:

1. No black screen: Lineage / Android boot animation visibly and continuously rendered. This does not alone establish complete OS boot.
2. A subsequent photograph showed the **fully rendered installed-app launcher screen** with status bar, app icons, Settings and ELHARIKA Launcher Lite. Therefore Android has passed BootAnimation and reached a working launcher UI, which had not happened in prior GPU experiments.
3. The initial built-in Launcher Lite was clearly underdesigned for a 12.2-inch landscape tablet. The screen in the photo was an app grid only; no professional dashboard or docks.

**Confirmed:** Physical display and launcher screen after r15p0 pair installation.  
**Not yet tested:** Wi-Fi, sleep/wake, S-Pen/Wacom, camera, audio, sensors, full system stability, battery endurance, reboot repeatability. Do not infer all subsystems are working.

## Why the launcher is primitive

`apps/launcher/src/main/java/org/elharika/launcher/MainActivity.java` implements one basic Java `LinearLayout` with a `GridView`, a search field and two buttons. The bare UI matches the physical screenshot and is not a Mali or Android platform bug.

## New optional standalone improvement

Implemented `apps/launcher-pro/` as a separate independent Android application, package **`org.elharika.launcher.pro`**. The original `org.elharika.launcher` remains installed, so user can switch back without modifying the proven boot/system graphics pair.

Includes:
- Adaptive 12.2-inch landscape/portrait layout; navy gradient background and rounded cards
- Localized Arabic, French and English resources
- Live clock/date, app counts, searchable app grid, shortcut panel, persistent favorites/dock
- Light/dark toggle, long-press app details and favorites; no INTERNET, overlay or root permission
- HOME intent filter so user can choose it through Android's Default Home settings

[GitHub Actions APK #42408669135](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42408669135) **SUCCESS**: APK packaging, Android 11 target API 30, minimum API 29, debug signing verification, SHA256 manifest. Artifact ID **13588203459**, APK filename **ELHARIKA-Launcher-Pro-Android11-v1.0-preview.apk**, bytes **38,427**, SHA256 **`7b4efd4c572d9dffe6d5a57093dbae185be65af82123edbb57c541a2fb9affc5`**. APK zip CRC independently checked. The APK has not yet been manually tested on the actual SM-P900.

**Installation:** Open APK with the tablet's Files app, permit that source if prompted, then press HOME and choose ELHARIKA Launcher Pro as default or use Settings > Apps > Default apps > Home. Return to ELHARIKA Launcher Lite if needed.

**Signing caveat:** CI debug certificate may differ across runs. A stable release signing key is required to upgrade without uninstalling the preview APK. This standalone APK is a preview, not a fully qualified ROM release.

**No changes to kernel BOOT, proprietary Mali ELF, system.img, or the system's existing launcher APK. Main remains unchanged, PR #7 draft.**
