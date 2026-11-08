#!/sbin/sh
# SM-P900 read-only probe for System mountpoint and proprietary Mali ELF.
# NO flash, wipe, mount, remount, reboot or BOOT partition read.
set -eu
FD=$2
case "$FD" in ''|*[!0-9]*) exit 1 ;; esac
ui() { printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$FD"; }
fail() { ui "STOP: $*"; exit 1; }
for tool in getprop awk sha256sum cat mktemp mv rm sync readlink; do
    command -v "$tool" >/dev/null 2>&1 || fail "Missing TWRP tool: $tool"
done
[ "$(getprop ro.product.device)" = v1awifi ] || fail "Not SM-P900/v1awifi"
case "$(getprop ro.bootloader)" in P900*) ;; *) fail "Unexpected bootloader" ;; esac
SD=""
for d in /external_sd /external_sd1; do
    [ -d "$d" ] && [ -w "$d" ] || continue
    if awk -v target="$d" '$2==target {ok=1} END {exit !ok}' /proc/mounts; then
        SD="$d"
        break
    fi
done
[ -n "$SD" ] || fail "Mount external Micro SDCard in TWRP first"
TARGET="$SD/elharika-mali-paths-report.txt"
if [ -e "$TARGET" ]; then
    TARGET=""
    for n in 01 02 03 04 05 06 07 08 09 10; do
        path="$SD/elharika-mali-paths-report-$n.txt"
        if [ ! -e "$path" ]; then TARGET="$path"; break; fi
    done
    [ -n "$TARGET" ] || fail "No free report name. Rename an older report first."
fi
TMP=$(mktemp /tmp/elharika-mali-paths.XXXXXX) || fail "RAM staging failed"
STAGED=""
cleanup() { rm -f "$TMP"; [ -z "$STAGED" ] || rm -f "$STAGED"; }
trap cleanup EXIT
umask 077

MOUNT_INFO=$(awk '
    $2=="/system" || $2=="/system_root" || $2=="/vendor" ||
    $2=="/mnt/system" || $2=="/mnt/vendor" || $2=="/system/system" {
        printf "%s%s:%s", sep,$2,$4; sep=","
    }' /proc/mounts)
MOUNT_STATUS=NO_RECOGNIZED_SYSTEM_MOUNT
[ -z "$MOUNT_INFO" ] || MOUNT_STATUS=KNOWN_SYSTEM_OR_VENDOR_MOUNT_VISIBLE

MALI_PATH=""
MALI_REAL=""
for candidate in \
    /system/system/vendor/lib/egl/libGLES_mali.so \
    /system/vendor/lib/egl/libGLES_mali.so \
    /system_root/system/vendor/lib/egl/libGLES_mali.so \
    /system_root/vendor/lib/egl/libGLES_mali.so \
    /vendor/lib/egl/libGLES_mali.so \
    /mnt/system/system/vendor/lib/egl/libGLES_mali.so \
    /mnt/system/vendor/lib/egl/libGLES_mali.so \
    /system/system/lib/egl/libGLES_mali.so \
    /system/lib/egl/libGLES_mali.so \
    /system_root/system/lib/egl/libGLES_mali.so \
    /system/system/vendor/lib/libGLES_mali.so \
    /system/vendor/lib/libGLES_mali.so; do
    [ -f "$candidate" ] || continue
    real=$(readlink -f "$candidate") || continue
    case "$real" in
        /system/*|/system_root/*|/vendor/*|/mnt/system/*|/mnt/vendor/*)
            MALI_PATH="$candidate"
            MALI_REAL="$real"
            break
            ;;
    esac
done

MALI_SHA=NOT_VISIBLE
MALI_STATUS=FILE_NOT_FOUND_IN_KNOWN_PATHS
if [ -n "$MALI_REAL" ]; then
    MALI_SHA=$(sha256sum "$MALI_REAL" | awk '{print $1}') || fail "Unable to hash Mali"
    MALI_STATUS=UNKNOWN_SHA
    if [ "$MALI_SHA" = 34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde ]; then
        MALI_STATUS=TESTED_R7P0_UK10_LIBRARY
    elif [ "$MALI_SHA" = 3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433 ]; then
        MALI_STATUS=OLDER_UK5_MISMATCH
    elif [ "$MALI_SHA" = a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839 ]; then
        MALI_STATUS=PINNED_R15P0_DONOR_LIBRARY
    fi
fi

{
    printf 'ELHARIKA SM-P900 MALI SYSTEM PATHS READONLY V2\n'
    printf 'device=v1awifi\nbootloader_family=P900\n'
    printf 'system_mount_status=%s\n' "$MOUNT_STATUS"
    printf 'system_mount_details=%s\n' "$MOUNT_INFO"
    for d in \
        /system/system/vendor/lib/egl \
        /system/vendor/lib/egl \
        /system_root/system/vendor/lib/egl \
        /system_root/vendor/lib/egl \
        /vendor/lib/egl \
        /mnt/system/system/vendor/lib/egl \
        /mnt/system/vendor/lib/egl \
        /system/system/lib/egl \
        /system/lib/egl; do
        [ -d "$d" ] && printf 'visible_egl_directory=%s\n' "$d"
    done
    printf 'mali_status=%s\nmali_path=%s\nmali_real_path=%s\nmali_sha256=%s\n' "$MALI_STATUS" "$MALI_PATH" "$MALI_REAL" "$MALI_SHA"
    printf 'boot_partition_modified=NO\nsystem_partition_modified=NO\ndata_partition_modified=NO\nflash_approved=NO\n'
    printf 'No partition was mounted, altered, or flashed by this diagnostic.\n'
} > "$TMP"
[ -s "$TMP" ] || fail "Internal report empty"
STAGED=$(mktemp "$SD/.elharika-mali-path-stage.XXXXXX") || fail "Cannot stage microSD"
cat "$TMP" > "$STAGED" || fail "microSD write failed"
[ -s "$STAGED" ] || fail "microSD output empty"
LEFT=$(sha256sum "$TMP" | awk '{print $1}')
RIGHT=$(sha256sum "$STAGED" | awk '{print $1}')
[ "$LEFT" = "$RIGHT" ] || fail "microSD hash mismatch"
[ ! -e "$TARGET" ] || fail "Output name occupied"
mv "$STAGED" "$TARGET" || fail "Cannot publish checked report"
STAGED=""
sync || fail "microSD sync failed"
ui "System mount: $MOUNT_STATUS"
ui "Mali ELF: $MALI_STATUS"
ui "Saved: $TARGET"
ui "No BOOT, SYSTEM or DATA changes."
