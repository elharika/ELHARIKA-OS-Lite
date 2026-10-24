# Complete build path and current limits

## Actual state

- Kernel and standalone apps compiled successfully in earlier CI runs.
- Stock system was inspected; 140 distinct files were staged with verified hashes, with nine unresolved requirements.
- Product sources now register `elharika_v1awifi-userdebug`, inherit only the v1awifi product, and add the two ELHARIKA applications and en_US/fr_FR/ar_MA locales. This is source integration, not a compiled system.
- The upstream base is AOSP-derived and requires the inherited upstream build infrastructure named in the code. It is not a vanilla AOSP checkout. Licenses and attribution remain intact.
- Configuration patches, extraction and staging tools have host-side tests. Hardware remains NOT_TESTED.

## Preparing a capable worker

`rom/platform-candidate.json` records a verified manifest commit for the Android 11 candidate. Its project branches are not all pinned. On a separately provisioned Linux x86_64 worker, install the Android build prerequisites and Repo, initialize Repo with the recorded URL/revision, install `rom/roomservice.xml` as a local manifest after checking duplicate project paths, then sync and run:

```sh
repo manifest -r -o elharika-platform-lock.xml
```

Do not claim reproducibility until the complete source lock is captured. A platform sync/build was NOT performed in this session. The preflight defaults (200 GiB free disk and 16 GiB RAM) are project planning thresholds, not measured Android 11 minima or a guarantee of success. The current local worker fails these defaults. GitHub standard-worker capacity is measured by the integration workflow; no paid or self-hosted worker has been provisioned.

## Integration and development build

After resolving the nine vendor requirements, generating reviewed vendor makefiles and syncing the platform:

```sh
python3 scripts/apply_device_fixes.py ANDROID_ROOT/device/samsung/universal5420-common
python3 scripts/prepare_product.py ANDROID_ROOT
python3 scripts/rom_preflight.py ANDROID_ROOT --report preflight.json
bash scripts/build-rom.sh ANDROID_ROOT NEW_BUILD_LOG_DIRECTORY
```

The product installer refuses to overwrite an existing vendor/elharika directory. The driver checks target v1awifi/ARM, preserves command failures through tee, limits job count, records a source manifest and build logs, and hashes boot.img/system.img only if compilation completes. `ELHARIKA_JOBS` can reduce parallelism. It does not generate a release ZIP, sign a final release or flash a device. Build-driver shell syntax and product installation were tested; the actual Android build commands remain unexecuted because the platform/vendor inputs are missing.

The inherited product fingerprint, duplicate base launcher/apps, SELinux policy compatibility and final branding need review during full integration. No claim of minimal RAM usage or complete app selection is made from these makefiles alone.

## Device observations and acceptance

When an authorized ADB connection to the tablet is available (recovery ADB is sufficient for the recovery subset):

```sh
python3 scripts/collect_device_qa.py --output NEW_DIAGNOSTICS_DIRECTORY
```

This collector requires exact SM-P900/v1awifi identity. It reads input capabilities, memory, kernel and SELinux state. In Android it additionally reads battery/thermal/input/graphics/sensors/audio diagnostics. It does not reboot, flash, inject input, change settings or automatically mark hardware working. Host fixture tests cover the recovery branch and rejection of wrong devices; it has not run on the physical tablet.

`qa/acceptance.json` records required acceptance checks with NOT_TESTED status. Tests need actual observations and saved evidence. A final flashable package and installation instructions cannot be approved before partition validation, successful build, boot, recovery and essential S Pen tests. Stock Odin tar.md5 archives and staged vendor folders must not be presented as TWRP-installable ELHARIKA packages.

## Remaining external and integration blockers

1. Resolve original-model graphics/audio/Bluetooth/DRM/compatibility dependencies; missing files cannot be replaced blindly.
2. Obtain a worker capable of a complete platform sync and build. Current GitHub jobs have built only smaller components and tools.
3. Compile Android and resolve actual compiler/linker/SELinux issues; only then inspect image/partition packaging.
4. Test on physical SM-P900, including pressure-sensitive handwriting, rotation, sleep/wake, GPU stability and battery drain.

No full ROM, hardware test result or performance comparison is fabricated. Repeating a CI tools test does not resolve these blockers.
