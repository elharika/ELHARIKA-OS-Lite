#!/usr/bin/env python3
"""Install custom product sources into an existing Android checkout; no build or flash."""
import argparse
from pathlib import Path
import shutil
import tempfile


def prepare(project, android):
    if not (android / 'build/envsetup.sh').is_file():
        raise ValueError('An existing Android platform checkout is required')
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
    return destination


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('android_root', type=Path)
    a = p.parse_args()
    print(prepare(Path(__file__).resolve().parents[1], a.android_root.resolve()))
