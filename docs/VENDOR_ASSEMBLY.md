# Experimental vendor tree assembly

Actual local assembly produced three vendor directories containing the 143 verified stock candidate files, Android.bp modules, product makefiles and board override files. All 143 generated source references resolve. Checksums for the complete assembled output passed. No proprietary binaries were published to GitHub.

Reproduce after the earlier stock extraction and candidate staging steps:

```sh
python3 scripts/assemble_vendor_tree.py CANDIDATE_BASELINE.json VERIFIED_STAGE NEW_VENDOR_OUTPUT
cd NEW_VENDOR_OUTPUT
sha256sum --check SHA256SUMS
```

The tool refuses existing output, validates original blob hashes through the rule generator, builds in a temporary directory, then renames the completed tree into place. This output represents the contents of an Android vendor directory, not a flashable vendor partition image. Do not overwrite an existing Android vendor tree with it wholesale.

## Applied source adaptation

The original mcDriverDaemon contains exactly one `/system/app` reference. The generated layout puts trustlets under `/vendor/app`; the equal-length replacement changes only that path. Input and output SHA-256 values are recorded in reports/vendor-assembly.json. Unexpected, repeated, or already-replaced paths are rejected. Other blob edits, including the inapplicable protobuf replacement, are not made.

This follows the path relocation used by the pinned upstream extraction script. It is still an experimental binary fixup. The pinned common SELinux file labels mcDriverDaemon as tee_exec; complete trustlet labels, access policy and runtime loading remain to be validated during the platform build/device tests.

## OpenCL aliases

Generated Android.mk creates libOpenCL.so, libOpenCL.so.1 and libOpenCL.so.1.1 symlinks under the vendor library directory, targeting /vendor/lib/egl/libGLES_mali.so. Rules are guarded for TARGET_DEVICE=v1awifi and depend explicitly on the Mali installed file. They have not been executed in a full Android build.

## Evidence and limits

Two host-side path-fixup tests passed, actual assembly ran, all file checksums passed, and all generated source references were checked. ELF build checks remain enabled. Soong compilation, library namespace compatibility, SELinux policy compilation, successful boot and hardware performance remain untested. No ROM ZIP, bootable system image or installation approval is claimed.
