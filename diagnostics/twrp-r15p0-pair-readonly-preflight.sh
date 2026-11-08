#!/sbin/sh
# SM-P900 read-only BOOT/Mali fingerprint. NEVER flashes or mounts partitions.
set -eu
OUTFD=$2
case "$OUTFD" in ''|*[!0-9]*) exit 1 ;; esac
ui() { printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$OUTFD"; }
fail() { ui "STOP: $*"; exit 1; }
for tool in getprop readlink head sha256sum awk wc tr cat mktemp mv rm sync; do
    command -v "$tool" >/dev/null 2>&1 || fail "Missing TWRP tool: $tool"
done
[ "$(getprop ro.product.device)" = v1awifi ] || fail "Not v1awifi recovery"
case "$(getprop ro.bootloader)" in P900*) ;; *) fail "SM-P900 bootloader not verified" ;; esac

BOOT_LINK=/dev/block/platform/dw_mmc.0/by-name/BOOT
[ -e "$BOOT_LINK" ] || fail "Missing BOOT partition link"
BOOT=$(readlink -f "$BOOT_LINK")
case "$BOOT" in /dev/block/mmcblk0p[0-9]*) ;; *) fail "Unexpected BOOT path" ;; esac
[ -b "$BOOT" ] || fail "BOOT is not a block device"

SD=""
for d in /external_sd /external_sd1; do
    [ -d "$d" ] && [ -w "$d" ] || continue
    if awk -v path="$d" '$2==path {ok=1} END {exit !ok}' /proc/mounts; then
        SD="$d"
        break
    fi
done
[ -n "$SD" ] || fail "Mount external microSD in TWRP. No partitions changed."

TARGET="$SD/elharika-r15-matched-pair-preflight.txt"
if [ -e "$TARGET" ]; then
    TARGET=""
    for n in 01 02 03 04 05 06 07 08 09 10; do
        c="$SD/elharika-r15-matched-pair-preflight-$n.txt"
        if [ ! -e "$c" ]; then TARGET="$c"; break; fi
    done
    [ -n "$TARGET" ] || fail "Report names occupied; rename one. No overwrite."
fi

TMP=$(mktemp /tmp/elharika-r15-check.XXXXXX) || fail "Cannot stage report"
BOOT_TEMP=$(mktemp /tmp/elharika-boot-sample.XXXXXX) || fail "Cannot stage BOOT sample"
STAGED=""
cleanup() {
    rm -f "$TMP" "$BOOT_TEMP"
    [ -z "$STAGED" ] || rm -f "$STAGED"
}
trap cleanup EXIT
umask 077

# These are SHA256 values for complete embedded boot.img prefixes in BOOT.
R7_SIZE=5437456
R15_SIZE=5462032
R7_SHA=f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0
R15_SHA=7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14
UK10_SHA=34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde
UK5_SHA=3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433
DONOR_SHA=a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839

head -c "$R15_SIZE" "$BOOT" > "$BOOT_TEMP" || fail "Cannot read BOOT"
SIZE=$(wc -c < "$BOOT_TEMP" | tr -d '[:space:]')
[ "$SIZE" = "$R15_SIZE" ] || fail "Short BOOT read"
R15_READ_SHA=$(sha256sum "$BOOT_TEMP" | awk '{print $1}')
head -c "$R7_SIZE" "$BOOT_TEMP" > "$TMP" || fail "BOOT prefix calculation failed"
R7_READ_SHA=$(sha256sum "$TMP" | awk '{print $1}')
BOOT_STATUS=UNKNOWN_DO_NOT_FLASH
if [ "$R15_READ_SHA" = "$R15_SHA" ]; then
    BOOT_STATUS=ORIGINAL_R15P0_REFERENCE
elif [ "$R7_READ_SHA" = "$R7_SHA" ]; then
    BOOT_STATUS=CURRENT_R7P0_KBUILD_FIXED
fi

# The user may mount System READ ONLY manually in TWRP.
MALI_PATH=""
for candidate in \
    /system/system/vendor/lib/egl/libGLES_mali.so \
    /system/vendor/lib/egl/libGLES_mali.so \
    /system_root/system/vendor/lib/egl/libGLES_mali.so \
    /vendor/lib/egl/libGLES_mali.so; do
    if [ -f "$candidate" ] && [ ! -L "$candidate" ]; then
        MALI_PATH="$candidate"
        break
    fi
done
MALI_STATUS=NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY
MALI_READ_SHA=NOT_VISIBLE
if [ -n "$MALI_PATH" ]; then
    MALI_READ_SHA=$(sha256sum "$MALI_PATH" | awk '{print $1}')
    MALI_STATUS=UNKNOWN_DO_NOT_FLASH
    if [ "$MALI_READ_SHA" = "$UK10_SHA" ]; then MALI_STATUS=TESTED_UK10_TRIAL; fi
    if [ "$MALI_READ_SHA" = "$UK5_SHA" ]; then MALI_STATUS=BLOCKED_UK5_BASE; fi
    if [ "$MALI_READ_SHA" = "$DONOR_SHA" ]; then MALI_STATUS=PINNED_DONOR_R15P0; fi
fi

{
    printf 'ELHARIKA SM-P900 READ-ONLY R15P0 PAIR PREFLIGHT\n'
    printf 'device=v1awifi\n'
    printf 'bootloader_family=P900\n'
    printf 'boot_status=%s\n' "$BOOT_STATUS"
    printf 'boot_r15_prefix_sha256=%s\n' "$R15_READ_SHA"
    printf 'boot_r7_prefix_sha256=%s\n' "$R7_READ_SHA"
    printf 'mali_status=%s\n' "$MALI_STATUS"
    printf 'mali_path=%s\n' "$MALI_PATH"
    printf 'mali_sha256=%s\n' "$MALI_READ_SHA"
    printf 'boot_partition_modified=NO\n'
    printf 'system_partition_modified=NO\n'
    printf 'data_partition_modified=NO\n'
    printf 'flash_approved=NO\n'
    printf 'physical_boot_verified=NO\n'
    printf 'This is diagnostic evidence only. No image or library was installed.\n'
} > "$TMP"

[ -s "$TMP" ] || fail "Internal report is empty"
STAGED=$(mktemp "$SD/.elharika-r15-preflight-stage.XXXXXX") || fail "microSD staging failure"
cat "$TMP" > "$STAGED" || fail "microSD write failed"
[ -s "$STAGED" ] || fail "microSD output is empty"
LEFT=$(sha256sum "$TMP" | awk '{print $1}')
RIGHT=$(sha256sum "$STAGED" | awk '{print $1}')
[ "$LEFT" = "$RIGHT" ] || fail "microSD checksum mismatch"
[ ! -e "$TARGET" ] || fail "Output name became occupied, no overwrite"
mv "$STAGED" "$TARGET" || fail "Cannot publish report"
STAGED=""
sync || fail "microSD sync failed"
ui "Read-only SM-P900 GPU pairing check complete."
ui "BOOT: $BOOT_STATUS"
ui "MALI: $MALI_STATUS"
ui "Report: $TARGET"
ui "No system or boot image changed."
