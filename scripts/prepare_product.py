#!/usr/bin/env python3
"""Install custom product sources into an existing Android checkout; no build or flash."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile


# The upstream board configuration is gated by this internal build variable.
ENV_OLD = """    else
        LINEAGE_BUILD=
    fi
    export LINEAGE_BUILD"""
ENV_NEW = """    elif [ "$1" = "elharika_v1awifi" ]; then
        LINEAGE_BUILD=v1awifi
    else
        LINEAGE_BUILD=
    fi
    export LINEAGE_BUILD"""


def product_environment(text):
    if text.count(ENV_NEW) == 1:
        return text
    if text.count(ENV_OLD) != 1:
        raise ValueError('Unexpected envsetup product detection; review before patching')
    return text.replace(ENV_OLD, ENV_NEW, 1)


def mobicore_selection(text):
    marker = '# ELHARIKA: exact-stock MobiCore trio is supplied by vendor prebuilts.'
    if marker in text:
        return text
    if hashlib.sha256(text.encode()).hexdigest() != 'b7e7aefde81c1332874e4bdbf4196e1d1afb69d0f26a5cb870042d78c3938728':
        raise ValueError('Unexpected pinned MobiCore rules; review duplicate providers')
    text = text.replace('# Client Library', marker + '\nifneq ($(TARGET_DEVICE),v1awifi)\n\n# Client Library', 1)
    return text.replace('# Provisioning Agent Shared Library', 'endif # stock MobiCore providers for v1awifi\n\n# Provisioning Agent Shared Library', 1)


def camera_selection(text):
    marker = '# ELHARIKA: use stock camera library, not the empty source stub.'
    if marker in text:
        return text
    if hashlib.sha256(text.encode()).hexdigest() != 'b95de996190349383d069d31cb6cbd0b432d0daec0b5fd19003143e7d23840a4':
        raise ValueError('Unexpected pinned camera rules; review library providers')
    text = text.replace('# libexynoscamera', marker + '\nifneq ($(TARGET_DEVICE),v1awifi)\n# libexynoscamera', 1)
    return text.replace('# libcamera\n', 'endif # stock camera library for v1awifi\n\n# libcamera\n', 1)


def prepare(project, android):
    if not (android / 'build/envsetup.sh').is_file():
        raise ValueError('An existing Android platform checkout is required')
    if not (android / 'cts/Android.bp').is_file():
        raise ValueError('Pinned CTS checkout is required for the product graph')
    environment = android / 'build/envsetup.sh'
    patched_environment = product_environment(environment.read_text())
    mobicore = android / 'hardware/samsung_slsi/exynos5420/mobicore/daemon/Android.mk'
    patched_mobicore = mobicore_selection(mobicore.read_text())
    camera = android / 'device/samsung/universal5420-common/camera/Android.mk'
    patched_camera = camera_selection(camera.read_text())
    destination = android / 'vendor/elharika'
    if destination.exists():
        raise ValueError('vendor/elharika already exists; refusing to overwrite')
    inputs = [project / 'rom/AndroidProducts.mk', project / 'rom/elharika_v1awifi.mk']
    for module in ['pen','launcher']:
        inputs += [project / 'apps' / module / 'Android.bp', project / 'apps' / module / 'src/main/AndroidManifest.xml']
    if any(not f.is_file() for f in inputs):
        raise ValueError('Project app/product sources are incomplete')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='elharika-prepare-') as tmp:
        staged = Path(tmp) / 'product'
        staged.mkdir()
        for name in ['AndroidProducts.mk','elharika_v1awifi.mk']:
            shutil.copyfile(project / 'rom' / name, staged / name)
        for module in ['pen','launcher']:
            module_dir = staged / 'apps' / module
            module_dir.mkdir(parents=True)
            shutil.copyfile(project / 'apps' / module / 'Android.bp', module_dir / 'Android.bp')
            shutil.copytree(project / 'apps' / module / 'src', module_dir / 'src')
        staged.rename(destination)
    environment.write_text(patched_environment)
    mobicore.write_text(patched_mobicore)
    camera.write_text(patched_camera)
    return destination


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('android_root', type=Path)
    a = p.parse_args()
    print(prepare(Path(__file__).resolve().parents[1], a.android_root.resolve()))
