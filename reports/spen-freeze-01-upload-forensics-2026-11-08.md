# SM-P900 S Pen drawing hard freeze — uploaded TWRP evidence (2026-11-08)

**Status: root cause unproven; do not flash or wipe.**

The user uploaded `ELHARIKA-SPEN-FREEZE-01.tgz` and the SHA256 sidecar. SHA256 verified:
`0fff12dfecc5d3d25165d2ada07d42762bfa5c8f0399092f18886295c5662012`.

## Confirmed

1. Four `system_server` ANR traces at 16:17:27, 16:18:41, 16:19:15 and 16:34:22 UTC show main thread in `HwBinder.getService` → `IKeyDisabler.getService` → `LineageHardwareManager`. Five `system_server_watchdog` reports (15:18–16:19 UTC) independently demonstrate the same boot-service wait.
2. A kernel snapshot contains `wacom_g5sp_i2c 8-0056: wacom_i2c_sync_lcd_freq: node file open fail, -2`; a later snapshot saved ~19:06 UTC additionally contains `wacom_i2c_sync_lcd_freq: Can't write node data` at uptime ~570.68 s.
3. Pinned `drivers/input/wacom/wacom_i2c.c` at kernel revision `de0cdcf10dcca77b400f15d83c1edf4f264a0f02` uses `/sys/class/tcon/tcon/psr_hsync` for V1A LCD sync and attempts O_RDWR|O_SYNC open and write. It handles open/write errors with unlock and delayed work. No evidence yet of IRQ deadlock or kernel panic.
4. No pstore files in the report. Collected `last_kmsg` ends in charger-mode restart; **not a demonstrated Wacom panic**. 10 latest tombstones are prior-day Bluetooth HCI aborts, not stylus. Five `system_app_wtf` are SystemUI KeyguardBouncer messages.
5. Recent Android DropBox entries end around 19:12 UTC. TWRP collected at approximately 19:26 UTC. There is no contemporaneous running-device input/GPU/kernel stack at the exact frozen stroke. The recovery `ro.build.fingerprint` is Omni Recovery Android 6.0.1, **not** a reliable identifier of the installed Android system.

## Temporal interpretation

The touch-fixed R15P0+One UI development package was built by GitHub Actions #42509941831 around 18:27 UTC. All captured KeyDisabler hangs occurred **before** that build. They do not demonstrate failure of that new package. The user subsequently confirmed in PR #10 that the latest R15P0 + S Pen Touch Fix image was installed when drawing froze. The combined image fails physical S Pen acceptance, while the cause of that freeze remains unproven.

## Action plan

- No wipe / restore / kernel or Mali swap on this evidence alone; preserve current matched R15P0 boot+system as found.
- Read-only identify the actually installed BOOT/SYSTEM provenance and inspect Android's sysfs node `/sys/class/tcon/tcon/psr_hsync` without writing.
- Capture noninvasive live diagnostics `logcat -b all -d`, `dumpsys input`, `dumpsys SurfaceFlinger`, `getevent -lp` if Android/ADB is safely available with finger input. Don't deliberately reproduce a hard freeze.
- Only then decide whether to modify Wacom LCD frequency sync, HIDL service discovery, graphics, or something else; protect with reversible rollback and on-device checks.

**Outcome: S Pen drawing stability fails physical acceptance, system-server KeyDisabler hang proven in earlier logs, Wacom LCD-sync warning proven, root cause of drawing freeze still UNKNOWN.**
