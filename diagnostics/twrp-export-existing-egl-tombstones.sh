#!/sbin/sh
# SM-P900 one-shot read-only native crash export from TWRP recovery.
# Does not mount partitions, flash, reboot, wipe, change permissions or install.
set -eu

OUTFD=$2
case "$OUTFD" in ''|*[!0-9]*) exit 1 ;; esac
ui() { printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$OUTFD"; }
fail() { ui "STOP: $*"; exit 1; }

for tool in getprop grep awk sha256sum mktemp rm cat; do
    command -v "$tool" >/dev/null 2>&1 || fail "TWRP missing required command: $tool"
done
[ "$(getprop ro.product.device)" = "v1awifi" ] || fail "Expected SM-P900/v1awifi recovery"
case "$(getprop ro.bootloader)" in P900*) ;; *) fail "SM-P900 bootloader not verified" ;; esac

# User controls TWRP mounts; never mount data or SD internally.
SD=""
for dest in /external_sd /external_sd1; do
    if [ -d "$dest" ] && [ -w "$dest" ] &&
       awk -v target="$dest" '$2==target {found=1} END {exit !found}' /proc/mounts; then
        SD="$dest"
        break
    fi
done
[ -n "$SD" ] || fail "Mount microSD in TWRP first. No partitions changed."
# Avoid an ambiguous empty scan if Data was not mounted or decrypted.
DATA_MOUNTED=$(awk '$2=="/data" {found=1} END {if(found) print 1; else print 0}' /proc/mounts)
[ "$DATA_MOUNTED" = 1 ] || fail "Data is not mounted. In TWRP > Mount, enable Data and retry; do NOT format."

TARGET="$SD/elharika-egl-crash-registers.txt"
[ ! -e "$TARGET" ] || fail "Existing output on microSD. Rename it first; no overwrite."
TMP=$(mktemp /tmp/elharika-egl-crash.XXXXXX) || fail "Cannot create temporary report"
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

umask 077
{
    printf 'ELHARIKA EGL / SM-P900 / READ ONLY TOMBSTONE SCAN\n'
    printf 'No system, boot, data or recovery partition changes were made.\n'
    printf 'Source selection requires both BootAnimation and eglp_swap_buffers.\n\n'
} > "$TMP"
COUNT=0
for dir in /data/tombstones /data/vendor/tombstones; do
    [ -d "$dir" ] || continue
    for path in "$dir"/tombstone_*; do
        [ -f "$path" ] && [ -r "$path" ] || continue
        case "$path" in *.pb) continue ;; esac
        grep -iq 'eglp_swap_buffers' "$path" || continue
        grep -iq 'bootanimation' "$path" || continue
        # Count only files actually exported, even if more tombstones exist.
        [ "$COUNT" -lt 5 ] || continue
        COUNT=$((COUNT+1))
        {
            printf '%s\n' "--- MATCH $COUNT : $path ---"
            # Limit output to process, signal, PC, registers, fault addr and ABI IDs.
            # Never export maps, stacks, unrelated processes, apps or user data.
            awk 'NR<=180 {
                t=tolower($0)
                if (t ~ /signal 11|fault addr|eglp_swap_buffers|build id:|>>>.*bootanimation|r0[[:space:]]|r1[[:space:]]|r2[[:space:]]|r3[[:space:]]|r4[[:space:]]|r5[[:space:]]|r6[[:space:]]|r7[[:space:]]|r8[[:space:]]|#00 pc/) {
                    print $0
                }
            }' "$path"
            printf '\n'
        } >> "$TMP"
    done
done
if [ "$COUNT" -eq 0 ]; then
    {
        printf 'NO_MATCHING_TOMBSTONE_FOUND\n'
        printf 'Data mount was verified by recovery; no matching readable BootAnimation text tombstone remains.\n'
        printf 'Older crash reports may have been rotated or removed. No Android reboot was requested.\n'
        printf 'No new Android boot was requested. Existing evidence is unchanged.\n'
    } >> "$TMP"
fi

cat "$TMP" > "$TARGET" || fail "microSD write failed (no system partition modified)"
ui "Read-only EGL scan completed. Matching tombstones: $COUNT"
ui "microSD file: elharika-egl-crash-registers.txt"
ui "SHA256: $(sha256sum "$TARGET" | awk '{print $1}')"
ui "No BOOT/system/data changes. Send this TXT for crash-register analysis."
