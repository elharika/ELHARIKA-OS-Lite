# ELHARIKA OS Lite — SM-P900 Android 11 boot branding (2026-11-08)

## Scope and physical behavior

The user requested that **ELHARIKA OS** appear prominently on powering on the Samsung SM-P900, similar to Samsung startup branding. The hardware **Samsung early splash screen** and the later **Android `bootanimation.zip`** are different stages. This change customizes only the second, software-controlled Android startup animation and does **not** alter the Exynos bootloader, initial Samsung splash, PIT, recovery, BOOT kernel or the proven paired `r15p0 + r15p0` Mali setup.

User provided physical photo confirming the paired R15P0 graphics path reaches the Android launcher UI. This must be preserved. No unnecessary Android ROM rebuild.

Android 11 formal bootanimation format is [AOSP FORMAT.md](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android11-mainline-conscrypt-release/cmds/bootanimation/FORMAT.md); AOSP BootAnimation.cpp may prioritize product or OEM animation over `/system/media`, so location must be checked on the *installed* filesystem rather than assumed.

## Created boot animation

- **ELHARIKA OS**, uppercase white typographic main wordmark, glowing turquoise OS suffix, slate/navy background, and `POWERED BY ANDROID 11`.
- Resolution `1280x800` (16:10, matches SM-P900 display aspect ratio), `24 fps`, 28 intro frames and 24 seamless/near-seamless loop frames; loops until Android startup terminates.
- AOSP `desc.txt`:
  ```
  1280 800 24
  p 1 0 part0
  p 0 0 part1
  ```
- `bootanimation.zip`: 4,329,318 bytes, SHA256 `c67585794cd65dd2352608fa80d735c548f37fac41d54794d565f48292d10a5c`; `ZIP_STORED` uncompressed parts, archive CRC checked and all 52 frames examined.
- Preview PNG generated, not a real photo of the SM-P900 screen.

## Optional installation and rollback

Created two **TWRP ZIPs** (not a full ROM), and a no-flash archive:
- `ELHARIKA-OS-BOOT-LOGO-INSTALL-TWRP.zip`: SHA256 `3a7ca1a15f044181f625da7f17be3f4781d5bfee93a580a4e2613df3e9f11cac`, 4,332,923 bytes.
- `ELHARIKA-OS-BOOT-LOGO-RESTORE-TWRP.zip`: SHA256 `e1c455e431f52b5f2d592af56522aea67374377d7bdc6566ead54727b0eab2ad`, 3,478 bytes.
- Both scripts require TWRP `ro.product.device=v1awifi`, bootloader P900, already-installed Android 11 API 30 and `ro.product.system.device=v1awifi`, correct SYSTEM partition alias, external microSD and system unmounted in TWRP. They mount **only** System ext4 temporarily and modify only the *already present, regular, non-symlink* `bootanimation.zip` chosen from `product/media/` then `media/`. If no known old file is visible, they fail without writing.
- The INSTALL ZIP extracts `payload/bootanimation.zip` and verifies SHA256 `c675...` before any System writes. It then **automatically** copies the old animation to a new numbered `ELHARIKA-BOOTANIM-ORIGINAL-xx` microSD directory and writes its hash and target path before replacing the existing file *in place* (preserving metadata/inode where possible). It validates post-write SHA and attempts to undo same-session errors. **No manual backup is required**.
- The RESTORE ZIP locates the latest verified microSD auto-backup, checks target path / original SHA / installed custom SHA, writes the original bytes back and verifies SHA. Keep the auto-backup folder if rollback might be needed.
- Does NOT touch `BOOT`, `RECOVERY`, `DATA`, `EFS`, `kernel`, `Mali`, any APK or `system.img`. One can keep using the recently built One UI Edition launcher independently.

## Important limitations

The ZIPs were syntax-checked, their members and CRCs audited, and SHA256SUMS verified **offline**. They are **NOT yet tested on the physical SM-P900/TWRP**; TWRP utilities and exact on-device bootanimation path may differ. No guarantee that the system will select this file if a higher-priority animation exists in an APEX/product path.

**Device steps:** Charge sufficiently, copy only the inner INSTALL and RESTORE ZIPs to microSD (not the outer package), TWRP > Mount: keep Micro SDCard mounted and **uncheck System**, TWRP > Install > select INSTALL. Don't wipe or format. After success reboot Android. To restore the older animation, go back to TWRP and choose RESTORE with the same microSD (auto-backup retained).

If the install reports any STOP error, do not bypass model/path checks or attempt to force a write. Collect a clear TWRP screenshot and inspect the exact installed image layout.

**Branch:** diagnostics/mali-r7p0-matched-boot-trial; PR #7 is still draft and the successful graphics pairing must not be overwritten.
