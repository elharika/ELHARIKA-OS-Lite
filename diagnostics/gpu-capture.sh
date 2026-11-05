#!/system/bin/sh
# Capture one boot only. No settings, permissions or hardware ioctls are changed.
REQUEST=/cache/elharika-gpu-capture.request
[ -f "$REQUEST" ] || exit 0
[ "$(cat "$REQUEST")" = ELHARIKA-GPU-CAPTURE-v1 ] || exit 1
umask 077
OUT=/cache/elharika-gpu-diagnostics
# Do not overwrite previous evidence. A second capture needs manual archival.
[ ! -e "$OUT" ] || exit 1
mkdir "$OUT" || exit 1
rm "$REQUEST"
exec > "$OUT/collector.log" 2>&1
echo 'ELHARIKA GPU capture v1; Android runtime, not recovery'
date
LOG_PID=
finish() {
    [ -z "$LOG_PID" ] || { kill "$LOG_PID" 2>/dev/null; wait "$LOG_PID" 2>/dev/null; }
    echo 'collector finished'
    sync
}
trap finish EXIT
logcat -b all -v threadtime -f "$OUT/logcat.txt" -r 1024 -n 3 &
LOG_PID=$!
for name in ro.hardware ro.board.platform ro.hardware.gralloc ro.hardware.hwcomposer ro.hardware.egl ro.product.device ro.build.version.sdk ro.treble.enabled ro.vndk.version; do
    echo "$name=$(getprop "$name")"
done
getenforce
cat /proc/cgroups
cat /proc/cmdline
cat /proc/mounts
if [ -r /proc/config.gz ]; then cp /proc/config.gz "$OUT/android-kernel-config.gz"; fi
for n in 0 1 2 3 4 5 6; do
    echo "=== snapshot $n ==="
    date
    ls -lZ /dev/mali* /dev/ion /dev/graphics/* /dev/dri/*
    for path in /sys/class/misc/mali0/device/gpuinfo /sys/class/misc/mali0/device/uevent /sys/class/misc/mali0/device/modalias /sys/class/misc/mali0/dev; do
        echo "=== $path ==="
        [ ! -r "$path" ] || cat "$path"
    done
    getprop init.svc.surfaceflinger
    getprop init.svc.vendor.hwcomposer-2-1
    ps -AZ
    [ "$n" = 6 ] || sleep 10
done
dmesg > "$OUT/android-dmesg.txt"
logcat -b all -d -v threadtime -t 3000 > "$OUT/logcat-final.txt"
