#!/sbin/sh
# SM-P900 Black Ice boot animation ONLY recovery. Never flashes a ROM.
set -eu
FD="$2"
case "$FD" in ''|*[!0-9]*) exit 1;; esac
ui(){ printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$FD"; }
stop(){ ui "STOP: $*"; exit 1; }
hash(){ sha256sum "$1" | awk '{print $1}'; }
NEW_SHA=f0538efc7e052bcf3e927ba214dcef7853dafc0dffd3293400ac66f4dc27fd4f
WORK=""; ACTIVE=0; WRITING=0
cleanup(){
  if [ "$ACTIVE" = 1 ]; then umount "$WORK/mnt" || ui "WARNING: System unmount failed"; fi
  if [ "$WRITING" = 0 ] && [ -n "$WORK" ]; then rm -rf -- "$WORK"; fi
}
trap cleanup EXIT
for t in getprop readlink sha256sum awk cat mount umount wc df mkdir mktemp rm sync grep tr; do
  command -v "$t" >/dev/null 2>&1 || stop "Missing recovery utility $t"
done
[ "$(getprop ro.product.device)" = v1awifi ] || stop "Not Samsung SM-P900"
case "$(getprop ro.bootloader)" in P900*) ;; *) stop "P900 bootloader not confirmed";; esac
SD=""
for d in /external_sd /external_sd1; do
  [ -d "$d" ] && [ -w "$d" ] || continue
  if awk -v p="$d" '$2==p{good=1}END{exit !good}' /proc/mounts; then SD="$d"; break; fi
done
[ -n "$SD" ] || stop "Mount external Micro SDCard in TWRP"
FOLDER=""
for n in 01 02 03 04 05 06 07 08 09 10; do
  p="$SD/ELHARIKA-BOOTANIM-ORIGINAL-$n"
  if [ -f "$p/bootanimation-original.zip" ] && [ -f "$p/TARGET.txt" ] && [ -f "$p/SHA256SUMS.txt" ]; then FOLDER="$p"; fi
done
[ -n "$FOLDER" ] || stop "Original animation backup absent; NO WRITE"
REL=$(cat "$FOLDER/TARGET.txt")
case "$REL" in media/bootanimation.zip|product/media/bootanimation.zip) ;; *) stop "Unknown backup target";; esac
EXPECTED=$(awk 'NR==1{print $1}' "$FOLDER/SHA256SUMS.txt")
case "$EXPECTED" in ''|*[!0-9a-f]*) stop "Invalid original SHA";; esac
LEN=$(printf '%s' "$EXPECTED" | wc -c | tr -d '[:space:]')
[ "$LEN" = 64 ] || stop "Bad original SHA length"
[ "$(hash "$FOLDER/bootanimation-original.zip")" = "$EXPECTED" ] || stop "Original copy damaged"
SYSTEM=$(readlink -f /dev/block/platform/dw_mmc.0/by-name/SYSTEM) || stop "SYSTEM block missing"
case "$SYSTEM" in /dev/block/mmcblk0p[0-9]*) ;; *) stop "Unexpected SYSTEM path";; esac
[ -b "$SYSTEM" ] || stop "SYSTEM is not block device"
while read -r source target flags; do
  actual=$(readlink -f "$source" 2>/dev/null || true)
  [ "$actual" != "$SYSTEM" ] || stop "Uncheck System in TWRP Mount"
done < /proc/mounts
FREE=$(df -Pk "$SD" | awk 'END{print $4}')
case "$FREE" in ''|*[!0-9]*) stop "Cannot check microSD free space";; esac
[ "$FREE" -ge 16384 ] || stop "Need 16 MB free on microSD"
WORK=$(mktemp -d "$SD/.elharika-recover-animation.XXXXXX") || stop "Cannot stage recovery"
mkdir "$WORK/mnt" || stop "Cannot prepare mountpoint"
mount -t ext4 -o rw "$SYSTEM" "$WORK/mnt" || stop "Cannot mount System; no changes made"
ACTIVE=1
ROOT="$WORK/mnt/system"
[ -d "$ROOT" ] && [ -f "$ROOT/build.prop" ] || stop "Wrong system layout"
grep -qx 'ro.build.version.sdk=30' "$ROOT/build.prop" || stop "Not Android 11 API30"
grep -qx 'ro.product.system.device=v1awifi' "$ROOT/build.prop" || stop "Wrong device"
TARGET="$ROOT/$REL"
[ -f "$TARGET" ] && [ ! -L "$TARGET" ] || stop "Animation absent/not regular"
[ "$(hash "$TARGET")" = "$NEW_SHA" ] || stop "Black Ice not installed; won't overwrite unknown file"
ui "Restoring verified original Android boot animation..."
WRITING=1
cat "$FOLDER/bootanimation-original.zip" > "$TARGET" || stop "Write interrupted; keep backup"
sync || stop "Sync failed; keep backup and remain in TWRP"
[ "$(hash "$TARGET")" = "$EXPECTED" ] || stop "Restore SHA mismatch; stay in TWRP"
WRITING=0
ui "SUCCESS: Original boot animation restored."
ui "BOOT/Mali/RECOVERY/DATA unchanged. Reboot normally."
