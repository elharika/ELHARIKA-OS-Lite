# SM-P900 S Pen troubleshooting: KeyDisabler boot-stall mitigation

**Status:** Proposed source-only bring-up patch, **not a tested ROM or flashable ZIP**.

## Evidence

The 2026-11-08 recovery-collected `ELHARIKA-SPEN-DIAG-01(2).tgz` contains seven
`system_server_watchdog` traces whose main thread blocks in
`HwBinder.getService()` for `vendor.lineage.touch@1.0::IKeyDisabler/default`
during `PhoneWindowManager` initialization.

Pinned `device/samsung/v1a-common/manifest.xml` declares `IKeyDisabler/default`,
while the pinned Samsung HIDL touch service registers `IKeyDisabler` only when
`KeyDisabler::isSupported()` can open its `KEY_DISABLER_NODE` for output.
The HAL's local header refers to `/sys/class/sec/sec_touchkey/input/enabled`;
the device family header lists `/sys/class/sec/sec_touchkey/touchkey_enabled`.
The actual device sysfs node and compiled header have **not** been observed
in a synchronized live capture. A missing/unsupported interface is the current
leading explanation for the service wait, not a proven pen-triggered reboot cause.

## Fix scope

`fix_v1a_keydisabler_manifest.py` removes **only** the one optional
`IKeyDisabler/default` declaration from the pinned v1a-common VINTF manifest.
It retains `ITouchscreenGesture` and both LiveDisplay interfaces, leaves the
Samsung HAL binary source untouched, and does not change S Pen input driver,
hover/pressure/button mapping, kernel, GPU, or firmware. This is an interim
boot-stall diagnostic measure. It is not a repair of button-disabling features;
they are deliberately no longer advertised.

The script accepts only the exact 848-byte original pinned XML or the exact
result SHA-256. It refuses drift and is idempotent:

```sh
python3 scripts/fix_v1a_keydisabler_manifest.py \
  "$ANDROID_ROOT/device/samsung/v1a-common"
python3 scripts/fix_v1a_keydisabler_manifest.py --check \
  "$ANDROID_ROOT/device/samsung/v1a-common"
python3 -m unittest discover -s tests -v
```

The system-image workflow applies the patch after syncing the pinned device
sources and before building. Boot kernel image is unchanged. Do **not** combine
old system/boot images without verifying the existing matching revision map.

## Remaining verification gates

1. Verify that the resulting built vendor manifest lacks `IKeyDisabler` but
   retains other necessary interfaces; validate system/vendor VINTF compatibility
   and SELinux policies.
2. Confirm the HAL process starts and its remaining interfaces register; record
   boot-time `hwservicemanager` and `logcat -b all`, and check there are no further
   watchdog stalls in `IKeyDisabler.getService`.
3. Test normal finger input first; only then perform a controlled Wacom
   hover, button and pressure test with continuous logs and a recovery plan.
4. Resolve independently the historical `libGLES_mali.so`/SurfaceFlinger
   problems before describing the OS as usable or stable.

**Safety:** Do not flash this source patch; it is not a TWRP installer. No wipe,
restore, or repartition is part of this change. Device validation pending.
