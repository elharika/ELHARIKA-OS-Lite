# SM-P900 — S Pen drawing freezes entire tablet (2026-11-08)

## Physical observation

User used the **S Pen for drawing**. The pen initially worked for a short time. Then the **whole tablet stopped responding to any input** until the user forcibly rebooted it.

This supersedes an earlier observation of an S Pen-triggered spontaneous reboot. The new symptom is a full system freeze with manual recovery, **not** a confirmed spontaneous power reset. It is not proof that the Wacom controller or the \`IKeyDisabler\` HIDL service is the primary root cause.

## Proven limits of earlier evidence

Older \`ELHARIKA-SPEN-DIAG-01(2).tgz\` includes seven \`system_server_watchdog\` reports awaiting \`IKeyDisabler/default\`, and historical graphics native crashes. The older \`kernel/last_kmsg.txt\` does **not** establish an S Pen IRQ kernel panic during this **new** drawing freeze; it ends in an orderly charger-mode \`Restarting system\` / \`sec_reboot\`. The older archive predates or is not temporally correlated with the latest freeze.

The Android 11 R15P0 + touch-HAL experimental system+boot package built as GitHub Actions #42509941831 has not been confirmed by the user to be installed. Do not assume it is the running build or that its source fix has been tested physically.

## Diagnostic strategy

1. Avoid deliberate reproduction by S Pen; use finger input when Android works.
2. Prefer capturing kernel \`pstore\` / \`last_kmsg\` plus \`system_server\` watchdogs/ANRs, DropBox and tombstones **from immediately after the existing frozen-boot incident**. Forced reboot may lose live buffers: absence of evidence does not prove absence of a kernel/GPU hang.
3. In TWRP, **Mount** Data (if decryptable) and Micro SDCard, then run \`ELHARIKA-SM-P900-SPEN-FREEZE-READONLY-COLLECTOR.zip\`. The script checks exact v1awifi/P900 device and only writes a report archive + SHA256 on the external microSD; it does **not** flash, mount, repartition, wipe, restore or reboot Android.
4. Send back \`ELHARIKA-SPEN-FREEZE-xx.tgz\` and mention which ROM/boot image is physically installed, approximate freeze time and drawing app. The report may contain private data; inspect it before sharing.
5. Correlate newest crash times with incident, examine \`wacom_i2c\` input/IRQ and touchscreen logs, EGL/Mali/ION/GPU faults, \`system_server\` ANRs/watchdogs, memory stalls and kernel resets. Only after evidence choose the smallest reversible correction.

## Safety

**No S Pen repair has been demonstrated.** No kernel patch, thermal/power workaround, EGL replacement, or Android setting can responsibly be asserted as a fix from this report alone. Do not flash a new ROM or wipe Data solely in response to the freeze. Preserve exact boot/system pairing and an independent working recovery/rollback before any future hardware trial.
