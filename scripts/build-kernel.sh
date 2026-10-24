#!/usr/bin/env bash
# Development kernel only. Never writes to a tablet or creates a flashable package.
set -euo pipefail
PROJECT=$(cd "$(dirname "$0")/.." && pwd)
: "${GCC49_ROOT:?Set GCC49_ROOT to the pinned Android ARM GCC 4.9 checkout}"
GCC49_ROOT=$(cd "$GCC49_ROOT" && pwd)
OUT=${KERNEL_OUT:-"$PROJECT/out/kernel"}
mkdir -p "$OUT" "$PROJECT/reports"
OUT=$(cd "$OUT" && pwd)
CC="$GCC49_ROOT/bin/real-arm-linux-androideabi-gcc"
# The pinned toolchain's wrapper needs /usr/bin/python. Use its actual binary.
[[ -x "$CC" ]] || { echo 'Pinned compiler missing'; exit 2; }
expected=43bf3bf040b873cb1334cdc0687a03d8d6f4b1c8
actual=$(git -C "$GCC49_ROOT" rev-parse HEAD)
[[ "$actual" == "$expected" ]] || { echo 'Toolchain revision mismatch'; exit 2; }
for tool in gcc make python3 bc lzop; do command -v "$tool" >/dev/null || { echo "Missing $tool"; exit 2; }; done
JOBS=${JOBS:-4}
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || exit 2
export KBUILD_BUILD_USER=elharika KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP='Mon Jan 8 00:00:00 UTC 2024'
args=(-C "$PROJECT/upstream/kernel" O="$OUT" ARCH=arm CROSS_COMPILE="$GCC49_ROOT/bin/arm-linux-androideabi-" CC="$CC")
make "${args[@]}" lineageos_v1awifi_defconfig 2>&1 | tee "$PROJECT/reports/kernel-config.log"
# Upstream defconfig intentionally disables modules: don't enable them just to
# satisfy a generic build command. Preserve the device's selected configuration.
make "${args[@]}" -j"$JOBS" zImage 2>&1 | tee "$PROJECT/reports/kernel-build.log"
python3 "$PROJECT/scripts/inspect-kernel.py" "$OUT" | tee "$PROJECT/reports/kernel-inspection.json"
echo 'Kernel compiled. Hardware runtime and Android boot remain UNTESTED.'
