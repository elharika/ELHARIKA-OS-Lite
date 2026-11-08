#!/sbin/sh
# PRE-TRIAL BACKUP ONLY. No flashing or mount commands. TWRP microSD.
set -eu
FD="$2"
case "$FD" in ''|*[!0-9]*) exit 1 ;; esac
ui() { printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$FD"; }
fail() { ui "STOP: $*"; exit 1; }
for cmd in getprop readlink head sha256sum awk wc df blockdev cat mktemp mkdir mv sync tr; do
    command -v "$cmd" >/dev/null 2>&1 || fail "Missing TWRP tool: $cmd"
done
[ "$(getprop ro.product.device)" = v1awifi ] || fail "Wrong recovery model: require v1awifi"
case "$(getprop ro.bootloader)" in P900*) ;; *) fail "Not a verified P900 bootloader" ;; esac
BOOT_LINK=/dev/block/platform/dw_mmc.0/by-name/BOOT
[ -e "$BOOT_LINK" ] || fail "Missing BOOT partition mapping"
BOOT=$(readlink -f "$BOOT_LINK") || fail "Cannot resolve BOOT device"
case "$BOOT" in /dev/block/mmcblk0p[0-9]*) ;; *) fail "Unexpected BOOT device path" ;; esac
[ -b "$BOOT" ] || fail "BOOT is not block device"
CAPACITY=$(blockdev --getsize64 "$BOOT") || fail "Cannot determine BOOT capacity"
[ "$CAPACITY" = 8388608 ] || fail "Unexpected BOOT capacity; refusing backup"
MALI=/system/vendor/lib/egl/libGLES_mali.so
[ -f "$MALI" ] || fail "Mali not visible: TWRP Mount > System (read-only)"
MALI_REAL=$(readlink -f "$MALI") || fail "Cannot resolve Mali path"
case "$MALI_REAL" in /system/*|/system_root/*|/vendor/*) ;; *) fail "Unsafe Mali path" ;; esac
[ -f "$MALI_REAL" ] || fail "Mali source not regular file"
CURRENT_BOOT_SHA=f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0
CURRENT_MALI_SHA=34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde
CURRENT_BOOT_IMAGE_LEN=5437456
FULL_BOOT_BYTES=8388608
BOOT_PREFIX=$(head -c "$CURRENT_BOOT_IMAGE_LEN" "$BOOT" | sha256sum | awk '{print $1}') || fail "BOOT fingerprint failed"
[ "$BOOT_PREFIX" = "$CURRENT_BOOT_SHA" ] || fail "Current BOOT differs from expected R7P0"
MALI_HASH=$(sha256sum "$MALI_REAL" | awk '{print $1}') || fail "Mali fingerprint failed"
[ "$MALI_HASH" = "$CURRENT_MALI_SHA" ] || fail "Current Mali differs from expected UK10"
SD=""
for d in /external_sd /external_sd1; do
    [ -d "$d" ] && [ -w "$d" ] || continue
    if awk -v p="$d" '$2==p {ok=1} END {exit !ok}' /proc/mounts; then
        SD="$d"
        break
    fi
done
[ -n "$SD" ] || fail "Mount external Micro SDCard in TWRP first"
FREE_KB=$(df -Pk "$SD" | awk 'END {print $4}') || fail "Cannot check microSD space"
case "$FREE_KB" in ''|*[!0-9]*) fail "microSD free space not numeric" ;; esac
[ "$FREE_KB" -ge 131072 ] || fail "microSD needs at least 128 MiB free"
FINAL=""
for n in 01 02 03 04 05 06 07 08 09 10; do
    path="$SD/ELHARIKA-R7P0-UK10-BACKUP-$n"
    if [ ! -e "$path" ]; then FINAL="$path"; break; fi
done
[ -n "$FINAL" ] || fail "Backup directories occupied. No overwrite."
umask 077
STAGE=$(mktemp -d "$SD/.elharika-backup-staging.XXXXXX") || fail "Cannot stage on microSD"
[ -d "$STAGE" ] || fail "No staging directory"
ui "Preparing recovery backup: NO writes to BOOT or SYSTEM."
ui "Do not reboot or remove microSD during copying."
head -c "$FULL_BOOT_BYTES" "$BOOT" > "$STAGE/BOOT.full-8MiB.backup" || fail "BOOT backup interrupted; incomplete hidden stage"
BYTES=$(wc -c < "$STAGE/BOOT.full-8MiB.backup" | tr -d '[:space:]')
[ "$BYTES" = "$FULL_BOOT_BYTES" ] || fail "BOOT copy length mismatch"
BACKED_BOOT_PREFIX=$(head -c "$CURRENT_BOOT_IMAGE_LEN" "$STAGE/BOOT.full-8MiB.backup" | sha256sum | awk '{print $1}')
[ "$BACKED_BOOT_PREFIX" = "$CURRENT_BOOT_SHA" ] || fail "Copied BOOT checksum mismatch"
FULL_BOOT_SHA=$(sha256sum "$STAGE/BOOT.full-8MiB.backup" | awk '{print $1}') || fail "Full BOOT SHA failed"
cat "$MALI_REAL" > "$STAGE/libGLES_mali.UK10.original.backup" || fail "Mali backup interrupted"
MALI_BACKUP_SHA=$(sha256sum "$STAGE/libGLES_mali.UK10.original.backup" | awk '{print $1}') || fail "Mali backup checksum failed"
[ "$MALI_BACKUP_SHA" = "$CURRENT_MALI_SHA" ] || fail "Mali backup differs from original"
[ "$(sha256sum "$MALI_REAL" | awk '{print $1}')" = "$CURRENT_MALI_SHA" ] || fail "Mali changed during capture"
{
    printf 'ELHARIKA SM-P900 R7P0 UK10 VERIFIED DUAL BACKUP V1\n'
    printf 'device=v1awifi\n'
    printf 'bootloader_family=P900\n'
    printf 'boot_source_image_sha256=%s\n' "$CURRENT_BOOT_SHA"
    printf 'boot_partition_backup_bytes=%s\n' "$FULL_BOOT_BYTES"
    printf 'boot_partition_backup_sha256=%s\n' "$FULL_BOOT_SHA"
    printf 'boot_partition_backup_image_prefix_sha256=%s\n' "$BACKED_BOOT_PREFIX"
    printf 'mali_source_path=%s\n' "$MALI"
    printf 'mali_source_real_path=%s\n' "$MALI_REAL"
    printf 'mali_backup_sha256=%s\n' "$MALI_BACKUP_SHA"
    printf 'backup_image=BOOT.full-8MiB.backup\n'
    printf 'backup_mali=libGLES_mali.UK10.original.backup\n'
    printf 'backup_verified=YES\n'
    printf 'rollback_tested_on_device=NO\n'
    printf 'boot_partition_modified=NO\nsystem_partition_modified=NO\ndata_partition_modified=NO\n'
    printf 'flash_approved=NO\n'
    printf 'Keep BOTH binary backup files in this microSD folder. TXT alone cannot restore.\n'
} > "$STAGE/VERIFIED_BACKUP.txt"
[ -s "$STAGE/VERIFIED_BACKUP.txt" ] || fail "Verification marker missing"
[ ! -e "$FINAL" ] || fail "Backup folder now occupied; refusing overwrite"
sync || fail "microSD flush failed"
mv "$STAGE" "$FINAL" || fail "Cannot publish verified backup; hidden stage may remain"
sync || fail "Cannot sync final backup"
ui "BACKUP VERIFIED: $FINAL"
ui "BOOT partition SHA: $FULL_BOOT_SHA"
ui "Mali UK10 SHA: $MALI_BACKUP_SHA"
ui "Send VERIFIED_BACKUP.txt only; KEEP both binary backups on microSD."
ui "No BOOT, SYSTEM or DATA partition modified."
