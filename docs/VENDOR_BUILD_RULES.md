# Candidate vendor build rules

`rom/generated-vendor/samsung/` contains actual generated Android.bp, product makefiles and empty board override files for the three audited device trees. They cover 143 unique hash-verified stock files: 14 ELF modules and 129 non-ELF copy entries. Proprietary binaries are not committed.

Reproduce generation from the experimental candidate baseline and verified staging folder:

```sh
python3 scripts/generate_vendor_rules.py CANDIDATE_BASELINE.json VERIFIED_STAGE NEW_OUTPUT
```

The generator reads DT_NEEDED from actual ARM32 binaries and declares shared library dependencies, install subdirectories and vendor placement. ELF files use cc_prebuilt_library_shared or cc_prebuilt_binary with `check_elf_files: true`; they are not silently copied through PRODUCT_COPY_FILES. Source hashes and architecture are checked before writing output. Existing output is not overwritten.

These files have NOT been compiled by Soong. Target module availability, vendor variants, symbol resolution, SONAME consistency, executable compatibility, duplicate module names elsewhere in the full platform, and namespace policy remain build-time checks. No allow_undefined_symbols or check_elf_files=false bypass was added. Generation success is not build success.

The original helper at LineageOS/android_tools_extract-utils (extract_utils.sh blob 455830f1f52f3f9d17d4c36cacc18da804d970d2) sends unprefixed list entries to PRODUCT_COPY_FILES and disables ELF checks for generated prebuilt modules. This project uses its own generator to keep these checks explicit.

## Blob fixup review

The pinned upstream common extraction script replaces a protobuf DT_NEEDED dependency in libMcClient. Actual P900XXS0BPL4 libMcClient needs libc, liblog, libm, libstdc++ and libstlport, and has no protobuf dependency. That replacement was **not applied**.

Stock mcDriverDaemon contains one `system/app` string and no `vendor/app` string. Upstream changes this location. That change remains pending review of trustlet installation and SELinux paths; it has not been silently applied. The generated layout is therefore still experimental and not boot-ready.

Upstream custom OpenCL symlinks and any required trustlet/fixup integration are not yet reproduced in these generated rules. Do not copy this output into a release and assume that the existence of vendor makefiles resolves runtime integration.

Tests use controlled fixtures to verify checked ELF module generation, install paths, hash rejection and architecture rejection. Actual generation also ran on the 143 staged stock files. No physical tablet test or Android platform compilation occurred.
