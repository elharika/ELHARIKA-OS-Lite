# Reviewed device configuration patches

These patches target only the exact universal5420 common source files pinned by `rom/roomservice.xml`, used by the SM-P900 device tree. They do not import firmware from another tablet.

Run after syncing hardware sources:

```sh
python3 scripts/apply_device_fixes.py ANDROID_ROOT/device/samsung/universal5420-common
```

The applier checks SHA-256 of every input and output. It refuses changed or partially patched sources, checks patch applicability before writing, and accepts a second invocation without further modifications. Upstream license headers remain intact.

Changes:

- Set `SELINUX_IGNORE_NEVERALLOWS` to false. The upstream file explicitly bypassed neverallow policy checks for legacy camera support. This patch restores build-time checks; it does not prove that the existing camera policy compiles or that runtime SELinux is enforcing. Any violations must be resolved during the full platform build rather than bypassed.
- Normalize AGC effect UUID `3b75f00-93ce-11e0-9fb8-0002a5d5c51b` to `03b75f00-93ce-11e0-9fb8-0002a5d5c51b`. This preserves the numerical UUID and makes the first field eight hexadecimal digits. All 17 configured UUIDs now have canonical spelling. No claim is made that the old spelling caused audible failures or that this validates the audio HAL.

Local integration testing used the actual pinned upstream files: patch application, repeat application, canonical unique UUIDs, enabled neverallow setting and rejection of local modifications without writes all passed. Full Android compilation and physical-device tests remain pending. These patches are stored in the project, but must be applied to the platform checkout using the command above; the remote upstream repositories are unchanged.

Other findings: the Bluetooth vendor configuration specifies `/vendor/firmware` but no fixed patch filename. That alone does not establish which stock HCD version the running controller will select. The original SM-P900 audio configuration names the 3.20.03 effects and contains the same AGC numeric identifier. Neither older stock effects nor Bluetooth firmware have been substituted into a release.
