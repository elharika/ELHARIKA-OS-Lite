#!/sbin/sh
# Read-only SM-P900 S Pen reboot crash collection. No ROM writes.
set -eu
FD="$2"
case "$FD" in ''|*[!0-9]*) exit 1;; esac
ui(){ printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$FD"; }
die(){ ui "STOP: $*"; exit 1; }
for t in getprop awk cat df mkdir cp ls head tar sha256sum date rm basename; do
 command -v "$t" >/dev/null 2>&1 || die "Missing recovery tool: $t"
done
[ "$(getprop ro.product.device)" = v1awifi ] || die "Only SM-P900 v1awifi supported"
case "$(getprop ro.bootloader)" in P900*) ;; *) die "P900 bootloader not verified";; esac
SD=""
for p in /external_sd /external_sd1; do
 [ -d "$p" ] && [ -w "$p" ] || continue
 if awk -v path="$p" '$2==path{a=1}END{exit !a}' /proc/mounts; then SD="$p"; break; fi
done
[ -n "$SD" ] || die "In TWRP Mount enable Micro SDCard"
awk '$2=="/data"{a=1}END{exit !a}' /proc/mounts || die "In TWRP Mount enable Data; do NOT format"
[ -d /data/system/dropbox ] || die "No crash reports found on mounted Data"
FREE="$(df -Pk "$SD" | awk 'END{print $4}')"
case "$FREE" in ''|*[!0-9]*) die "Cannot read microSD free space";; esac
[ "$FREE" -ge 131072 ] || die "Need 128 MB free on microSD"
umask 077
DIR=""
for n in 01 02 03 04 05 06 07 08 09 10; do
 p="$SD/ELHARIKA-SPEN-DIAG-$n"
 if [ ! -e "$p" ] && [ ! -e "$p.tgz" ]; then DIR="$p"; break; fi
done
[ -n "$DIR" ] || die "Previous report names occupied (01-10); no overwrite"
mkdir -p "$DIR/kernel" "$DIR/dropbox" "$DIR/tombstones" || die "Cannot make report folder"
{
 echo "ELHARIKA OS Lite SM-P900 stylus reboot diagnostics"
 date
 echo "Device: $(getprop ro.product.device)"
 echo "Bootloader: $(getprop ro.bootloader)"
 echo "Captured in TWRP recovery, not live Android"
 echo "Sensitive app/device crash information may be present. Review before sharing."
} > "$DIR/README.txt"
ui "Collecting previous reboot/crash logs WITHOUT touching OS..."
if [ -f /proc/last_kmsg ] && [ -r /proc/last_kmsg ]; then
 cp /proc/last_kmsg "$DIR/kernel/last_kmsg.txt" 2>/dev/null || true
fi
for f in /sys/fs/pstore/console-ramoops* /sys/fs/pstore/dmesg-ramoops*; do
 [ -f "$f" ] && [ -r "$f" ] || continue
 cp "$f" "$DIR/kernel/$(basename "$f")" 2>/dev/null || true
done
DB=/data/system/dropbox
for pattern in 'system_server_watchdog*' 'system_server_crash*' 'system_app_native_crash*' 'system_app_crash*' 'system_app_wtf*' 'SYSTEM_LAST_KMSG*' 'SYSTEM_BOOT*'; do
 ls -t "$DB"/$pattern 2>/dev/null | head -n 7 | while IFS= read -r f; do
  [ -f "$f" ] || continue
  cp "$f" "$DIR/dropbox/$(basename "$f")" 2>/dev/null || true
 done
done
n=0
for f in /data/tombstones/tombstone_*; do
 [ -f "$f" ] || continue
 [ "$n" -lt 8 ] || break
 cp "$f" "$DIR/tombstones/$(basename "$f")" 2>/dev/null || true
 n=$((n+1))
done
tar -czf "$DIR.tgz" -C "$DIR" . || die "Report compression failed"
[ -s "$DIR.tgz" ] || die "Report empty"
sha256sum "$DIR.tgz" > "$DIR.tgz.sha256" || die "Checksum failed"
rm -rf -- "$DIR" || true
ui "SUCCESS: $(basename "$DIR").tgz saved on microSD"
ui "No System/BOOT/Mali/Data changes. Send this single archive."
