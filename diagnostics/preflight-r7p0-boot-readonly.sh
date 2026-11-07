#!/sbin/sh
# Read-only SM-P900 TWRP preflight. DOES NOT FLASH, FORMAT OR MOUNT PARTITIONS.
# Run in TWRP terminal: sh /external_sd/ELHARIKA-SM-P900-r7p0-READONLY-PREFLIGHT.sh
# If System is not mounted, vendor Mali hash will show NOT_VISIBLE.
set -eu
OLD_BOOT_SHA='7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14'
OLD_SIZE=5462032
MALI_OLD_SHA='3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433'
MALI_UK10_SHA='34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde'

for tool in getprop readlink head sha256sum awk wc tr rm cat; do
    command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: missing $tool"; exit 1; }
done
DEVICE=$(getprop ro.product.device)
BOOTLOADER=$(getprop ro.bootloader)
echo '=== ELHARIKA SM-P900 READ-ONLY PREFLIGHT ==='
echo "recovery_device=$DEVICE"
echo "bootloader=$BOOTLOADER"
if [ "$DEVICE" != v1awifi ]; then
    echo 'STOP: unexpected recovery device; no changes were made.'
    exit 1
fi
case "$BOOTLOADER" in P900*) ;; *) echo 'STOP: unexpected bootloader; no changes were made.'; exit 1 ;; esac
BOOT_LINK='/dev/block/platform/dw_mmc.0/by-name/BOOT'
if [ ! -e "$BOOT_LINK" ]; then
    echo 'STOP: BOOT partition symlink not found; no changes were made.'
    exit 1
fi
BOOT_REAL=$(readlink -f "$BOOT_LINK")
case "$BOOT_REAL" in /dev/block/mmcblk0p[0-9]*) ;; *) echo 'STOP: unexpected BOOT partition path.'; exit 1 ;; esac
echo "boot_device=$BOOT_REAL"
TMP="/tmp/elharika-boot-prefix.$$"
trap 'rm -f "$TMP"' 0 1 2 3 15
if ! head -c "$OLD_SIZE" "$BOOT_REAL" > "$TMP"; then
    echo 'STOP: cannot read boot partition.'
    exit 1
fi
N=$(wc -c < "$TMP" | tr -d '[:space:]')
if [ "$N" != "$OLD_SIZE" ]; then
    echo "STOP: short BOOT read ($N bytes)."
    exit 1
fi
HASH=$(sha256sum "$TMP" | awk '{print $1}')
echo "boot_prefix_sha256=$HASH"
if [ "$HASH" = "$OLD_BOOT_SHA" ]; then
    echo 'boot_check=ORIGINAL_REFERENCE_MATCH'
else
    echo 'boot_check=MISMATCH_DO_NOT_FLASH'
fi
MALI_FILE=''
for candidate in \
    /system/system/vendor/lib/egl/libGLES_mali.so \
    /system/vendor/lib/egl/libGLES_mali.so \
    /system_root/system/vendor/lib/egl/libGLES_mali.so \
    /vendor/lib/egl/libGLES_mali.so; do
    if [ -f "$candidate" ]; then
        MALI_FILE=$candidate
        break
    fi
done
if [ -z "$MALI_FILE" ]; then
    echo 'mali_check=NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY_THEN_RERUN'
else
    MALI_HASH=$(sha256sum "$MALI_FILE" | awk '{print $1}')
    echo "mali_path=$MALI_FILE"
    echo "mali_sha256=$MALI_HASH"
    if [ "$MALI_HASH" = "$MALI_UK10_SHA" ]; then
        echo 'mali_check=UK10_TRIAL_CANDIDATE_MATCH'
    elif [ "$MALI_HASH" = "$MALI_OLD_SHA" ]; then
        echo 'mali_check=ORIGINAL_OLDER_BLOB_MATCH'
    else
        echo 'mali_check=UNRECOGNIZED_DO_NOT_FLASH'
    fi
fi
echo 'This was a READ-ONLY check. No partitions or images were modified.'
echo 'Do NOT flash the r7p0 boot image until boot backup, Mali pairing and restore order are reviewed.'
