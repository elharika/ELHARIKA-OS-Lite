#!/usr/bin/env python3
"""Package complete experimental SM-P900 Android 11 SYSTEM+BOOT from an
already source-verified system.ext4 with donor r15p0 Mali installed in-place.

Do not release as working without physical boot tests. This process doesn't
touch the tablet, userdata, EFS or recovery. Do not use original mismatched
system.img directly.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import zipfile

BOOT_SHA="7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14"
BOOT_SIZE=5462032
SYSTEM_BYTES=2299998208
SYSTEM_SHA_ORIGINAL_SPARSE="a0e5904b2bb20bfb350090bef50e465514a482d71c67870a86d9711ebdc03ead"
DONOR_SHA="a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839"
NAME="ELHARIKA-OS-Lite-SM-P900-Android11-R15P0-SPEN-TOUCH-EXPERIMENTAL.zip"

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def validate_inputs(image, boot, marker):
    image,boot,marker=Path(image),Path(boot),Path(marker)
    if image.stat().st_size!=SYSTEM_BYTES:raise ValueError("System ext4 geometry mismatch")
    if boot.stat().st_size!=BOOT_SIZE or sha(boot)!=BOOT_SHA:
        raise ValueError("Original r15p0 BOOT doesn't match pinned physical graphics pair")
    if not marker.is_file():
        raise ValueError("No proof that donor Mali was installed in system image")
    report=json.loads(marker.read_text())
    exact={
        "original_system_sparse_sha256":SYSTEM_SHA_ORIGINAL_SPARSE,
        "installed_mali_sha256":DONOR_SHA,
        "installed_mali_path":"/system/vendor/lib/egl/libGLES_mali.so",
        "installed_system_device":"v1awifi",
        "installed_system_sdk":"30",
        "original_inode_unchanged":True,
        "original_owner_mode_xattrs_unchanged":True,
        "original_bootanimation_preserved":True,
        "source_ext4_e2fsck_ok":True,
        "touch_source_ci_validated":True,
        "touch_vintf_keydisabler_absent":True,
        "touch_vintf_gesture_preserved":True,
        "touch_sdk_service_getter_patched":True,
        "flash_approved":False
    }
    # The chosen One UI Edition Android 11 home APK must be integrated in System.
    # Keep the basic ROM launcher as a fallback rather than disabling Home handling.
    exact.update({
        "oneui_launcher_included":True,
        "oneui_launcher_system_path":"/system/app/ELHARIKAOneUI/ELHARIKAOneUI.apk",
        "oneui_launcher_package":"org.elharika.oneui",
        "original_rom_launcher_preserved":True,
        "original_bootanimation_preserved":True,
    })
    for key,value in exact.items():
        if report.get(key)!=value: raise ValueError(f"Missing/mismatched safety condition: {key}")
    launcher_sha=report.get("oneui_launcher_apk_sha256","")
    if len(launcher_sha)!=64 or any(v not in "0123456789abcdef" for v in launcher_sha):
        raise ValueError("One UI launcher APK hash evidence missing or malformed")
    return report

def package(image,boot,marker,out):
    image,boot=Path(image),Path(boot)
    validated=validate_inputs(image,boot,marker)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    template=(Path(__file__).resolve().parents[1]/"installer/update-binary.in").read_text()
    size=SYSTEM_BYTES+BOOT_SIZE
    vals={
        "SYSTEM_SIZE":str(SYSTEM_BYTES),
        "SYSTEM_SHA":sha(image),
        "BOOT_SIZE":str(BOOT_SIZE),
        "BOOT_SHA":BOOT_SHA,
        "REQUIRED_KB":str(size//1024+131072),
    }
    for key,value in vals.items():
        marker="@"+key+"@"
        if template.count(marker)==0:raise ValueError("Installer parameter missing "+key)
        template=template.replace(marker,value)
    if "@SYSTEM_" in template or "@BOOT_" in template or "@REQUIRED_KB@" in template:
        raise ValueError("Unresolved installer guard")
    subprocess.run(["sh","-n"],input=template,text=True,check=True,timeout=10)
    critical=[
        "getprop ro.product.device","BOOT","SYSTEM",
        'dd if="$WORK/system.ext4" of="$SYSTEM"',
        'dd if="$WORK/boot.img" of="$BOOT"',
        "sha256sum -c SHA256SUMS",
    ]
    for guard in critical:
        if guard not in template:raise ValueError("Installer missing guarded operation: "+guard)
    readme=(
        "ELHARIKA OS Lite experimental Android 11 CLEAN REINSTALL for SM-P900/v1awifi.\n"
        "Uses independently built touch-fixed Android 11 system with exact R15P0 Mali ELF and R15P0 BOOT.\n"
        "Compiled and filesystem-audited OFFLINE. The clean reinstall package is NOT device-tested.\n"
        "Does not touch userdata (Data), EFS, Recovery, bootloader or partition table.\n"
        "Requires external microSD with >=2.5GiB free, unmounted System in TWRP, power >=50%.\n"
        "Only install the inner TWRP ZIP, never the outer Actions artifact.\n"
        "WARNING: Full Android reinstall from scratch may require Wipe Data; that erases apps,\n"
        "settings and personal files stored in Data. This installer NEVER wipes Data itself.\n"
        "ELHARIKA One UI Edition is preinstalled as an Android HOME app.\n"
        "Keep ELHARIKA Launcher Lite as fallback. At first HOME choose One UI Edition.\n"
        "Custom Black Ice boot animation is intentionally NOT included.\n"
        "The source image from run 42289790703 is NOT independently bootable with its old Mali.\n"
        "Do NOT flash only BOOT or only Mali.\n"
        "Android camera/GPS unsupported in this development build; no verified security patch level.\n"
        "Successful CI and first-ever launcher boot do not guarantee repeat-boot stability.\n"
    )
    manifest={
        "status":"SYSTEM_R15_MALI_AND_BOOT_R15_PAIRED_EXPERIMENTAL",
        "hardware_tested_on_clean_reinstall":False,
        "flash_approved":False,
        "source_system_run":42289790703,
        "original_system_sparse_sha256":SYSTEM_SHA_ORIGINAL_SPARSE,
        "source_r15_boot_run":42067803567,
        "boot_sha256":BOOT_SHA,
        "donor_r15_mali_sha256":DONOR_SHA,
        "oneui_launcher_apk_sha256":validated["oneui_launcher_apk_sha256"],
        "oneui_launcher_package":"org.elharika.oneui",
        "oneui_launcher_system_path":"/system/app/ELHARIKAOneUI/ELHARIKAOneUI.apk",
        "original_rom_launcher_preserved":True,
        "full_raw_system_sha256":vals["SYSTEM_SHA"],
        "raw_system_bytes":SYSTEM_BYTES,
        "full_system_flash":True,
        "wipes_data":False,
        "source_integrity_check":validated
    }
    target=out/NAME
    # Keep ZIP32; the raw ext4 member is >2GB but <4GB. TWRP ZIP64 may fail.
    old_limit=zipfile.ZIP64_LIMIT
    zipfile.ZIP64_LIMIT=0xffffffff
    try:
        with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=False) as z:
            def add(name,data,mode=0o644):
                info=zipfile.ZipInfo(name,(2026,11,8,0,0,0))
                info.external_attr=(0o100000|mode)<<16
                info.create_system=3;info.compress_type=zipfile.ZIP_DEFLATED
                if isinstance(data,Path):
                    info.file_size=data.stat().st_size
                    with data.open("rb") as source,z.open(info,"w") as dest:
                        shutil.copyfileobj(source,dest,1024*1024)
                else:z.writestr(info,data)
            add("META-INF/com/google/android/update-binary",template,0o755)
            add("META-INF/com/google/android/updater-script","# Exact model and SHA gated updater\n")
            add("system.ext4",image)
            add("boot.img",boot)
            add("README.txt",readme)
            add("verification.json",json.dumps(manifest,indent=2))
    finally: zipfile.ZIP64_LIMIT=old_limit
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None or len(z.namelist())!=6:raise ValueError("ZIP CRC/structure check failed")
        if any(q.extract_version>20 for q in z.infolist()):raise ValueError("ZIP64 unsupported by TWRP")
    (out/"SHA256SUMS.txt").write_text(sha(target)+"  "+NAME+"\n")
    (out/"INSTALLATION-NOTES.txt").write_text(readme)
    (out/"verification.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return {"zip":NAME,"zip_size":target.stat().st_size,"zip_sha256":sha(target),
            "system_sha256":vals["SYSTEM_SHA"],"boot_sha256":BOOT_SHA,"hardware_tested":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--system",required=True,type=Path)
    p.add_argument("--boot",required=True,type=Path)
    p.add_argument("--marker",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(package(a.system,a.boot,a.marker,a.out),indent=2))
