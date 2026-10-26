# Android 11 system-image build: SELinux blocker (2026-10-26)

Build [40353097741](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/40353097741) completed source sync, stock SM-P900 vendor assembly, lunch, and reached 29,734/68,117 Ninja actions (43%). It failed at `sepolicy_neverallows` after 47m28s; `system.img` was **not produced or validated**. The already separate boot-image run remains structural evidence only.

The policy compiler reported 16 neverallow failures. Grouped conflicts:

- Legacy HAL1 camera: cameraserver/mediaserver registering `cameraserver_service` and `fwk_camera_hwservice`, and mediaserver finding `hal_camera_hwservice`. The legacy camera policy from pinned device-lineage-sepolicy is involved. Camera architecture needs a specific policy/service review rather than suppressing neverallow assertions.
- sysfs writes: cbd to `sysfs_sec_switch`, touch HAL to `sysfs_sec_touchscreen`, wifi HAL to `sysfs_wifi`, init/sensors HAL to `sysfs_input`. Each write and its target labeling must be traced to the device-specific producer and restricted or removed as appropriate.
- Other: `system_server` execmem; `cbd` dac_override; graphics composer access to `audio_device`; sensors HAL writes to `system_data_file`. These need source and runtime path audits.

The complete compiler messages and locked platform manifest are in the run's evidence artifact. The safety gate is intentionally active: do not set `SELINUX_IGNORE_NEVERALLOWS` to true, mark this a successful build, or flash development images. Next iteration should trace each allow to its originating .te rule, remove unjustified access or use appropriately labeled interfaces, run `sepolicy_neverallows` as a focused target, then retry `systemimage`. Physical hardware verification remains outstanding.
