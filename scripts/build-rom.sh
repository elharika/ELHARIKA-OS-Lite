#!/usr/bin/env bash
# Development build driver. Produces build outputs only; never flashes or releases.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo 'Usage: build-rom.sh ANDROID_SOURCE_ROOT NEW_LOG_DIRECTORY' >&2
  exit 64
fi
project_root="$(cd "$(dirname "$0")/.." && pwd)"
android_root="$(realpath "$1")"
log_dir="$(realpath -m "$2")"
if [[ -e "$log_dir" ]]; then echo 'Log directory must be new' >&2; exit 64; fi
mkdir -p "$log_dir"
python3 "$project_root/scripts/rom_preflight.py" "$android_root" --report "$log_dir/preflight.json" 2>&1 | tee "$log_dir/preflight.log"
jobs="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["suggested_jobs"])' "$log_dir/preflight.json")"
if [[ -n "${ELHARIKA_JOBS:-}" ]]; then
  if ! [[ "$ELHARIKA_JOBS" =~ ^[1-9][0-9]*$ ]]; then echo 'ELHARIKA_JOBS must be a positive integer' >&2; exit 64; fi
  if (( ELHARIKA_JOBS > jobs )); then echo "Requested parallelism exceeds preflight recommendation ($jobs)" >&2; exit 64; fi
  jobs="$ELHARIKA_JOBS"
fi
cd "$android_root"
# Android environment scripts are not nounset-clean.
set +u
source build/envsetup.sh
lunch elharika_v1awifi-userdebug 2>&1 | tee "$log_dir/lunch.log"
set -u
if [[ "$(get_build_var TARGET_DEVICE)" != v1awifi ]]; then echo 'Wrong target device' >&2; exit 1; fi
if [[ "$(get_build_var TARGET_ARCH)" != arm ]]; then echo 'Wrong target architecture' >&2; exit 1; fi
repo manifest -r -o "$log_dir/built-source-manifest.xml"
# No release ZIP is produced by this command. Inspect raw images before packaging.
set +u
m -j"$jobs" bootimage systemimage 2>&1 | tee "$log_dir/build.log"
set -u
product_out="$(get_build_var PRODUCT_OUT)"
[[ -s "$product_out/boot.img" && -s "$product_out/system.img" ]]
sha256sum "$product_out/boot.img" "$product_out/system.img" > "$log_dir/SHA256SUMS"
printf '%s\n' 'COMPILED DEVELOPMENT IMAGES ONLY. Hardware NOT_TESTED. No release approval.' > "$log_dir/BUILD_STATUS.txt"
