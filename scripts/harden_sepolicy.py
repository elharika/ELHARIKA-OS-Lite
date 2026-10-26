#!/usr/bin/env python3
"""Remove two prohibited grants from exact pinned Wi-Fi device policy."""
from pathlib import Path
import sys

ORIGINAL = {
    "system_server.te": "# system_server.te\n\nallow system_server mobicore_data_file:dir r_dir_perms;\n\nallow system_server sysfs_rndis:file w_file_perms;\n\nallow system_server self:process execmem;\n\nget_prop(system_server, exported_camera_prop)\nget_prop(system_server, userspace_reboot_exported_prop)\nget_prop(system_server, userspace_reboot_config_prop)\nget_prop(system_server, vendor_radio_prop)\n",
    "cbd.te": "# cbd.te\n\nallow cbd {\n    radio_device\n    radio_qos_device\n}:chr_file rw_file_perms;\n\nallow cbd bin_nv_data_efs_file:file rw_file_perms;\nallow cbd efs_file:file w_file_perms;\n\nallow cbd {\n    proc_net\n    proc_stat\n}:file r_file_perms;\n\nallow cbd sysfs_sec_switch:dir r_dir_perms;\n\nallow cbd {\n    sysfs_power\n    sysfs_sec_switch\n    sysfs_usb_power_writable\n}:file rw_file_perms;\n\nallow cbd properties_device:dir r_dir_perms;\n\n##### FIXME ######\nallow cbd self:capability dac_override;\n##### FIXME ######\n\nset_prop(cbd, radio_prop)\n",
    "hal_sensors_default.te": "# hal_sensors_default.te\n\nallow hal_sensors_default system_data_file:dir create_dir_perms;\nallow hal_sensors_default system_data_file:file create_file_perms;\n\nallow hal_sensors_default sensors_data_file:dir create_dir_perms;\nallow hal_sensors_default sensors_data_file:file create_file_perms;\n\nallow hal_sensors_default sysfs_muic:dir r_dir_perms;\n\nallow hal_sensors_default sysfs_input:file rw_file_perms;\n\nallow hal_sensors_default sysfs_input:lnk_file r_file_perms;\n",
}
REMOVALS = {
    "system_server.te": "allow system_server self:process execmem;\n",
    "cbd.te": "allow cbd self:capability dac_override;\n",
    "hal_sensors_default.te": "allow hal_sensors_default system_data_file:dir create_dir_perms;\nallow hal_sensors_default system_data_file:file create_file_perms;\n\n",
}

def apply(root):
    root = Path(root)
    directory = root / "sepolicy/vendor"
    updates = {}
    for name, original in ORIGINAL.items():
        current = (directory / name).read_text()
        target = original.replace(REMOVALS[name], "")
        if current == target:
            continue
        if current != original or original.count(REMOVALS[name]) != 1:
            raise ValueError("Unrecognized policy: " + name)
        updates[name] = target
    for name, target in updates.items():
        (directory / name).write_text(target)
    return len(updates)

if __name__ == "__main__":
    print("Hardened policy files:", apply(sys.argv[1]))
