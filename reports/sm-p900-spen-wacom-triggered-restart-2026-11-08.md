# SM-P900 ELHARIKA OS Lite — S Pen-triggered restart, then stalled boot animation

Date: 2026-11-08

## Physical user report

Android 11 returned to the launcher and was usable with finger input. User then reported that **using S Pen causes the tablet to restart**, and subsequent boot stays at the original blue/cyan stroke animation. This is a stronger regression signal than prior generic boot-animation observations; do **not** blame boot logo, launcher, Mali or system_server individually without new logs. It may be a kernel failure in Wacom I²C IRQ path or an Android service/watchdog reaction; requires last-kmsg/pstore/DropBox evidence to decide.

## Source inspection

Pinned kernel source `exynos5420/android_kernel_samsung_exynos5420` commit `de0cdcf10dcca77b400f15d83c1edf4f264a0f02`.

- `drivers/input/wacom/wacom_i2c.c` uses a threaded Wacom interrupt which calls `wacom_i2c_coord()`.
- `drivers/input/wacom/wacom_i2c_func.c` `wacom_i2c_coord()` reads the input I²C packet, processes hover/contact/pressure/side-button events, and reports ABS_X/ABS_Y/ABS_PRESSURE/BTN_TOUCH through Linux Input.
- `wacom_i2c_sync_lcd_freq()` handles failed `filp_open()` and logs error `node file open fail, -2`; an older user kernel excerpt contained exactly that warning. It is **not proof** of current restart trigger and must not be patched blindly.
- Previous physical `/data/system/dropbox` screenshots contained `system_server_watchdog`, `system_app_native_crash` and `system_app_wtf`; records are not yet temporally correlated with S Pen reboot.

## Non-invasive action

Do not use the S Pen until cause is established; use finger only if tablet is currently usable. Avoid wiping Data, full ROM reinstall, graphics/kernel changes, repeated deliberate crashes, or replacing any firmware blindly.

Created a **single install read-only TWRP crash collector**:
- workflow [#42501689079](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42501689079) **SUCCESS**;
- artifact `ELHARIKA-SM-P900-SPEN-READONLY-LOGS` ID `13625369396`, outer size 2204 bytes; inside the artifact ZIP use `ELHARIKA-SM-P900-SPEN-READONLY-CRASH-COLLECTOR.zip`;
- in TWRP Mount, enable Data and Micro SDCard, choose inner ZIP with Install, and supply generated `ELHARIKA-SPEN-DIAG-xx.tgz` from microSD;
- collector reads existing `/proc/last_kmsg`, `/sys/fs/pstore`, recent `/data/system/dropbox` and tombstones; writes only to the external microSD, not system/boot/data/efs/recovery;
- scripts reviewed with `sh -n`, static forbidden-write guard, packaging ZIP CRC and SHA verification. **Not yet physically TWRP tested**.
- If logs are absent or Data cannot mount, STOP instead of formatting; collected logs may include private data and should be reviewed before sharing.

**STATUS:** user-observed S Pen reboot reproduced by report, root cause not confirmed, no kernel change or flash-ready fix claimed. Maintain proven r15p0 matched BOOT+Mali and optional launcher.
