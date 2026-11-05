#!/system/bin/sh
# Capture one boot only. No settings, permissions or hardware ioctls are changed.
trace_surfaceflinger() {
    trace_out=$1
    expected_executable=$2
    trace_binary=$3
    poll_limit=${4:-1500}
    trace_pid=
    last_pid=
    attempts=0
    poll=0
    trap '[ -z "$trace_pid" ] || { kill "$trace_pid" 2>/dev/null; wait "$trace_pid" 2>/dev/null; }' EXIT
    trap 'exit 0' TERM INT
    # Bound each trace file (1024-byte units are not assumed; even 512-byte
    # shell blocks keep each file at most 2 MiB), and capture at most 3 starts.
    ulimit -f 2048 || return 1
    "$trace_binary" -V
    while [ "$poll" -lt "$poll_limit" ] && [ "$attempts" -lt 3 ]; do
        poll=$((poll + 1))
        candidate=$(getprop init.svc_debug_pid.surfaceflinger)
        case "$candidate" in ''|*[!0-9]*) sleep 0.02; continue;; esac
        if [ "$candidate" != "$last_pid" ] &&
           [ "$(readlink "/proc/$candidate/exe" 2>/dev/null)" = "$expected_executable" ]; then
            last_pid=$candidate
            attempts=$((attempts + 1))
            echo "Attaching strace to verified SurfaceFlinger pid=$candidate attempt=$attempts"
            "$trace_binary" -f -tt -y -s 128 -e trace=open,openat,ioctl,mmap2,close \
                -o "$trace_out/surfaceflinger-strace-$attempts.txt" -p "$candidate" &
            trace_pid=$!
            wait "$trace_pid"
            echo "strace exit=$? for pid=$candidate"
            trace_pid=
        fi
        sleep 0.02
    done
    echo "strace watcher finished; attempts=$attempts"
}
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
echo 'ELHARIKA GPU capture v3 with bounded syscall tracing; Android runtime'
date
LOG_PID=
WATCH_PID=
finish() {
    [ -z "$WATCH_PID" ] || { kill "$WATCH_PID" 2>/dev/null; wait "$WATCH_PID" 2>/dev/null; }
    [ -z "$LOG_PID" ] || { kill "$LOG_PID" 2>/dev/null; wait "$LOG_PID" 2>/dev/null; }
    echo 'collector finished'
    sync
}
trap finish EXIT
logcat -b all -v threadtime -f "$OUT/logcat.txt" -r 1024 -n 3 &
LOG_PID=$!
trace_surfaceflinger "$OUT" /system/bin/surfaceflinger /system/bin/strace > "$OUT/strace-watcher.log" 2>&1 &
WATCH_PID=$!
for name in ro.hardware ro.board.platform ro.hardware.gralloc ro.hardware.hwcomposer ro.hardware.egl ro.product.device ro.build.version.sdk ro.treble.enabled ro.vndk.version; do
    echo "$name=$(getprop "$name")"
done
getenforce
cat /proc/cgroups
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
    [ "$n" = 6 ] || sleep 10
done
dmesg > "$OUT/android-dmesg.txt"
logcat -b all -d -v threadtime -t 3000 > "$OUT/logcat-final.txt"
