# SM-P900 vendor staging

Run on the expanded, inspected P900XXS0BPL4 system image:

```sh
python3 scripts/stage_stock_vendor.py \
  --system-image /path/to/system.ext4 \
  --baseline reports/stock-P900XXS0BPL4-vendor-comparison.json \
  --output /path/to/new-staging-directory
cd /path/to/new-staging-directory
sha256sum --check SHA256SUMS
```

The actual stock image produced 140 distinct files (approximately 35 MiB). Every staged file passed SHA-256 validation. The previous 141 count was a count of present requirement entries, including an identical duplicate of `etc/wifi/bcmdhd_mfg.bin_4339_a0`. The tool removes only identical source/hash/destination duplicates and rejects conflicting destinations. Nine requirements remain missing; see the committed staging report. No alternate-version substitutions are performed.

The destination layout follows the source audit mapping. This directory is **not** an Android vendor partition or a flashable ROM. File execution modes, SELinux labels, HAL declarations and Android prebuilt modules still require integration. A successful extraction does not certify runtime compatibility. No proprietary bytes are committed to GitHub; extraction is reproducible from the user's stock image and recorded hashes. Review redistribution rights before publishing binaries.

The current blockers to a full platform build remain: a complete pinned Android platform manifest, resolved vendor/HAL dependencies, a sufficiently provisioned build worker, and subsequent physical SM-P900 testing. The current local worker has approximately 23 GiB free disk and 9.7 GiB total RAM; no full platform source tree has been synced here. The completed GitHub builds cover kernel/apps/tools, not Android system.img.

Current upstream workstation sizing documentation targets the latest Android branch and should not be represented as a measured Android 11 minimum: https://source.android.com/docs/setup/start/requirements . A full Android 11 build resource requirement has not been measured by this project.
