#!/sbin/sh
# SM-P900 read-only post-freeze evidence collector. Writes reports ONLY to external microSD.
# Never formats, mounts, remounts, flashes, reboots, or changes Android files.
set -eu
FD="${2:-}"
case "$FD" in ''|*[!0-9]*) exit 1;; esac
ui() { printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$FD"; }
die() { ui "STOP: $*"; exit 1; }
for t in getprop awk cat df mkdir cp ls head tar sha256sum date rm basename uname; do
  command -v "$t" >/dev/null 2>&1 || die "Missing recovery tool: $t"
done
[ "$(getprop ro.product.device)" = v1awifi ] || die "For SM-P900/v1awifi only"
case "$(getprop ro.bootloader)" in P900*) ;; *) die "P900 bootloader not verified" ;; esac
SD=""
for p in /external_sd /external_sd1; do
  [ -d "$p" ] && [ -w "$p" ] || continue
  if awk -v path="$p" '$2==path{found=1} END{exit !found}' /proc/mounts; then
    SD="$p"
    break
  fi
done
[ -n "$SD" ] || die "In TWRP > Mount enable Micro SDCard. No automatic mount."
FREE="$(df -Pk "$SD" | awk 'END{print $4}')"
case "$FREE" in ''|*[!0-9]*) die "Cannot determine microSD free space";; esac
[ "$FREE" -ge 131072 ] || die "128 MiB of free microSD space required"
umask 077
BASE=""
for n in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20; do
  p="$SD/ELHARIKA-SPEN-FREEZE-$n"
  if [ ! -e "$p" ] && [ ! -e "$p.tgz" ] && [ ! -e "$p.tgz.sha256" ]; then
    BASE="$p"
    break
  fi
done
[ -n "$BASE" ] || die "All report slots 01-20 used; do not overwrite older reports"
mkdir -p "$BASE/kernel" "$BASE/dropbox" "$BASE/tombstones" "$BASE/anr" "$BASE/device" || die "Cannot create report folder"
{
  echo 'ELHARIKA OS Lite — SM-P900 S Pen drawing FREEZE evidence'
  date
  echo "Device: $(getprop ro.product.device)"
  echo "Bootloader: $(getprop ro.bootloader)"
  echo "Android system build fingerprint (from recovery getprop; may be absent): $(getprop ro.build.fingerprint)"
  echo 'Collected in TWRP after FORCED restart; absence of a kernel panic does not rule out GPU/UI hangs.'
  echo 'This ZIP is not a ROM. It does not fix S Pen, reboot or flash partitions.'
  echo 'Crash reports may contain private data; review them before sharing.'
} > "$BASE/README.txt"
{
  uname -a
  cat /proc/cmdline 2>/dev/null || true
} > "$BASE/device/recovery-kernel.txt"
ui 'Collecting previous-boot kernel / Android crash evidence to microSD only...'
if [ -f /proc/last_kmsg ] && [ ! -L /proc/last_kmsg ] && [ -r /proc/last_kmsg ]; then
  cp /proc/last_kmsg "$BASE/kernel/last_kmsg.txt" 2>/dev/null || true
fi
for f in /sys/fs/pstore/console-ramoops* /sys/fs/pstore/dmesg-ramoops* /sys/fs/pstore/pmsg-ramoops*; do
  [ -f "$f" ] && [ ! -L "$f" ] && [ -r "$f" ] || continue
  cp "$f" "$BASE/kernel/$(basename "$f")" 2>/dev/null || true
done
if awk '$2=="/data"{found=1} END{exit !found}' /proc/mounts; then
  if [ -d /data/system/dropbox ]; then
    DB=/data/system/dropbox
    for pattern in 'system_server_watchdog*' 'system_server_anr*' 'system_server_crash*' 'system_app_native_crash*' 'system_app_crash*' 'system_app_anr*' 'system_app_wtf*' 'data_app_native_crash*' 'data_app_anr*' 'SYSTEM_LAST_KMSG*' 'SYSTEM_BOOT*'; do
      ls -t "$DB"/$pattern 2>/dev/null | head -n 5 | while IFS= read -r f; do
        [ -f "$f" ] && [ ! -L "$f" ] || continue
        cp "$f" "$BASE/dropbox/$(basename "$f")" 2>/dev/null || true
      done
    done
  fi
  if [ -d /data/anr ]; then
    ls -t /data/anr/* 2>/dev/null | head -n 4 | while IFS= read -r f; do
      [ -f "$f" ] && [ ! -L "$f" ] || continue
      cp "$f" "$BASE/anr/$(basename "$f")" 2>/dev/null || true
    done
  fi
  for root in /data/tombstones /data/vendor/tombstones; do
    [ -d "$root" ] || continue
    ls -t "$root"/tombstone_* 2>/dev/null | head -n 10 | while IFS= read -r f; do
      [ -f "$f" ] && [ ! -L "$f" ] || continue
      cp "$f" "$BASE/tombstones/$(basename "$f")" 2>/dev/null || true
    done
  done
else
  echo 'Data was not mounted. Not formatted or mounted automatically. Android crash records unavailable.' >> "$BASE/README.txt"
fi
{
  date
  ls -l "$BASE/kernel" "$BASE/dropbox" "$BASE/tombstones" "$BASE/anr" 2>/dev/null || true
} > "$BASE/device/collected-files.txt"
tar -czf "$BASE.tgz" -C "$BASE" . || die "Could not compress report on microSD"
[ -s "$BASE.tgz" ] || die "Empty report"
sha256sum "$BASE.tgz" > "$BASE.tgz.sha256" || die "Cannot verify report checksum"
rm -rf -- "$BASE"
ui "SUCCESS: $(basename "$BASE").tgz saved to microSD; NO system/boot/data writes"
ui 'Send that single .tgz archive. Do not reproduce the freeze to obtain logs.'
