# Modem policy correction and sensor blocker

Source-generated CI run 40458639784 confirmed exactly two remaining assertions: cbd writing sysfs_sec_switch and hal_sensors_default writing sysfs_input. All project checks passed in that run. Camera hosting and init changes now have source-regeneration evidence, but no hardware validation.

The new modem patch preserves reads of sysfs_sec_switch and removes its broad file write/append grant. It does not relabel sysfs or alter neverallow assertions, other switch types, USB power permissions or sensor permissions. The common tree includes inherited modem policy although this target is Wi-Fi. No cbd executable appears in the assembled stock vendor checksums. Runtime and installed-package validation remain required.

Real checkpolicy replay of this new run's compiler inputs, with the equivalent modem rule change placed in the policy rule section, reports one remaining assertion: hal_sensors_default sysfs_input:file write. An earlier diagnostic placed an allow after filesystem contexts and was invalid; that result is not counted. The successful reproduction is saved in evidence/selinux-modem-candidate-2026-10-27.json. This remains an incomplete policy compile, not a passed build.

Two modem regression tests passed; seven locally available init/camera/modem tests passed together. CI executes the complete repository suite. Next run also extracts filtered static sysfs/input hints from the exact SHA-256 verified stock sensor library. These are investigation hints, not proof of paths accessed at runtime, and do not justify blanket write access or claiming sensor/S Pen functionality.
