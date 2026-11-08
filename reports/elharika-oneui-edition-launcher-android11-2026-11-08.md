# ELHARIKA One UI Edition — native Android 11 tablet launcher prototype

**Date:** 2026-11-08  
**User feedback:** The two earlier ELHARIKA Launcher Lite/Pro applications look primitive compared to the Samsung Galaxy Tab S10+ One UI Home screen. This is a *new separate* application, not another styling patch to the old launcher.

## Actual shipped implementation

Package: `org.elharika.oneui`, minimum API 29, target API 30, Java Android SDK, independent build under `apps/launcher-oneui`. The original `org.elharika.launcher` and `org.elharika.launcher.pro` stay available as alternate HOME apps.

UI is **One UI-inspired**, not a Samsung One UI proprietary APK and not a literal reproduction of Samsung icons, firmware services or app store assets:
- Full-screen soft curved gradient/wave wallpaper; three selectable color profiles
- Tablet landscape home, clock and date card, battery percentage, configurable icon scale
- Three persisted home pages, native application shortcut launch, app information menus
- Bottom persistent dock, add/remove favorites, swipe-up app drawer with fast local search
- Editable home: drag-to-reorder, drag-to-create simple folders, app menu move to next page
- System AppWidgetHost integration: picker, bind approval, render supported installed widgets
- Arabic/French/English string resources
- No network, accessibility, root, overlay, boot/system change or Samsung-only dependency

The native user/system taskbar inside other apps, DeX, Samsung Notes, Samsung widget providers and Samsung-specific One UI animations **are not supplied** by an independent launcher APK. Widget availability depends on installed providers.

## Verified GitHub artifact

[GitHub Actions run #42453092239](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42453092239) **SUCCESS**:
- Java/AAPT compiled with Android SDK 35, Java 17 / Gradle 8.7
- Debug APK signature verified; target Android 11 API 30 and minimum API 29 verified with `aapt`
- Artifact ID **13605973529** `ELHARIKA-ONE-UI-EDITION-ANDROID11-TABLET-APK`
- Direct inner APK `ELHARIKA-OneUI-Edition-SM-P900-Android11-v1.apk`: **67,539 bytes**, SHA256 `efbdf19a6c1865ef75046fa7c28cfd103fb28a07dd8670cfe0efb7542a54b305`
- GitHub artifact ZIP CRC checked independently on extraction, resulting APK copied and validated

## Limitations / next test gate

- **Field test pending** on physical SM-P900: launcher startup, native widget picker, icon drag/drop, rotation/landscape sizing and persisting folders. Build/signature/API tests do NOT imply 100% functionality.
- Generated APK has a non-persistent DEBUG signing identity; a future release-signing key must be set up for seamless upgrades.
- A later milestone could replace this simple custom home engine with an AOSP Launcher3-derived production workspace for stronger drag/drop, resizable widgets and lifecycle support. Avoid inventing a systemwide Samsung tablet taskbar.
- If startup fails: Settings > Apps > Default apps > Home app > ELHARIKA Launcher Lite / Pro. DO NOT flash an old UK5 system or alter the functioning r15p0 BOOT/Mali.
- Keep PR #7 on development branch; do not touch `main` until physical UI verification.
