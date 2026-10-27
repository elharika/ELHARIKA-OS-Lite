# SELinux init permission correction

The pinned common init policy grants init write/append access to all sysfs_input files. Reviewed init.universal5420.rc and init.samsung.rc use chmod/chown for input nodes (including sec_epen/input/enabled), not content writes to those input paths. The patch preserves read and setattr access, removes broad write/append, leaves other sysfs grants and all labels unchanged. Hardware validation remains required, including imported scripts and resolved sysfs paths.

Validation: two new unit tests passed (pinned transformation/idempotence and rejection of original/patched source drift). Replayed captured run 40406491838 with the equivalent expanded-rule change in both compiler inputs: real checkpolicy reports nine assertion failures instead of ten. This is a candidate replay, not a fresh Android source regeneration or a successful full policy build. Both compiler checks still must pass in CI. No hardware tests or flash approval.

Camera investigation: pinned frameworks/av 7db8eb3de32436269109f8168d24f19d90cb24ce main_mediaserver.cpp starts CameraService under NO_CAMERA_SERVER; mediaserver Android.bp inherits camera_in_mediaserver_defaults. Legacy policy assigns camera service ownership to mediaserver while platform policy assigns it to cameraserver. Do not delete the legacy flag or assertions merely to pass compilation: align service ownership and build selection first. Remaining failures: seven camera assertions, cbd sysfs_sec_switch write, sensors sysfs_input write.

Workflow integrates the init patch. No costly Android rebuild was launched because replay already proves other blockers remain. Original CI evidence is unchanged.
