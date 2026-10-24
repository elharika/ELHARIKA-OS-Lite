#!/usr/bin/env python3
import argparse,hashlib,json,struct,sys
from pathlib import Path
REQUIRED=['CONFIG_INPUT_WACOM=y','CONFIG_EPEN_WACOM_G9PLL=y','CONFIG_MACH_UNIVERSAL5420=y','CONFIG_V1A=y','CONFIG_V1A_WIFI=y','CONFIG_SECURITY_SELINUX=y']
def inspect(root):
 image=root/'arch/arm/boot/zImage';data=image.read_bytes();config=(root/'.config').read_text();lines=set(config.splitlines())
 magic=len(data)>=48 and struct.unpack_from('<I',data,36)[0]==0x016f2818
 missing=[k for k in REQUIRED if k not in lines]
 return {'zimage_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'arm_zimage_magic_valid':magic,'missing_required_config':missing,'modules_enabled':'CONFIG_MODULES=y' in lines,'hardware_status':'not_tested','boot_image_status':'not_built','config_sha256':hashlib.sha256(config.encode()).hexdigest(),'source_kernel_version':'3.4.113'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('kernel_out',type=Path);a=p.parse_args();r=inspect(a.kernel_out);print(json.dumps(r,indent=2));sys.exit(not r['arm_zimage_magic_valid'] or bool(r['missing_required_config']))
