# Experimental Android 11 minimal vendor profile

This is an integration option, not a built or boot-tested ROM. It preserves the exact-model hardware objective and does not substitute firmware from another model.

Changes to the pinned common device source:

- Omit aptX encoder blob. aptX encoding is not offered by this profile. Other Bluetooth codecs still need runtime validation.
- Omit the four Widevine files and their two VINTF service declarations. Widevine-protected playback is not supported; no DRM bypass is implemented. Existing generic DRM and ClearKey source modules remain.
- Remove the old proprietary libaudioroute requirement and add the Android 11 source module to PRODUCT_PACKAGES. The module exists with vendor_available=true in `LineageOS/android_system_media` commit `b432f63fcbf6fecb43631ac8ef0454fa770182a4`, path `audio_route/Android.bp`. It and its callers still require actual compilation/link and runtime tests.

The common source revision remains `b018612a7939d3a4ab8900e3d03ac1ca608546a0`. Apply before generating vendor makefiles:

```sh
python3 scripts/apply_minimal_profile.py ANDROID_ROOT/device/samsung/universal5420-common
python3 scripts/minimal_vendor_baseline.py \
  reports/stock-P900XXS0BPL4-vendor-comparison.json NEW_MINIMAL_BASELINE.json
python3 scripts/stage_stock_vendor.py \
  --system-image /path/to/system.ext4 \
  --baseline NEW_MINIMAL_BASELINE.json --output NEW_MINIMAL_STAGING
```

The patch is independent of the earlier policy/audio-UUID patch: it modifies different files. Its applier checks exact before/after hashes and refuses source drift. Do not retain previously generated vendor makefiles with Widevine/aptX modules. The source profile is not yet automatically selected by build-rom.sh.

Actual extraction from the inspected P900XXS0BPL4 system image produced **139 distinct files**, all SHA-256 verified. The derived list has 144 requirement entries, 140 present entries including one duplicate, and four absent paths:

- vendor/firmware/bcm4350_V0301.0609.hcd
- vendor/lib/liblvverx_3.25.00.so
- vendor/lib/liblvvetx_3.25.00.so
- vendor/lib/libstlport.so

This does not mean only four problems remain. Stock Mali/camera compatibility, source-built audio routing, blob fixups, namespaces, vendor module generation and a complete platform build are still unverified. Existing stock alternatives have not been approved or substituted. Original upstream provenance annotations remain visible; remaining foreign-model blob pins are not authorization to import them.

Local validation: exact patch application, repeat application, retained core dependencies, removed Widevine declarations, source-drift rejection, and derived-list accounting passed. Runtime hardware tests remain NOT_TESTED. No final installation package is produced.
