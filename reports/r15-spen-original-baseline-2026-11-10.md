# SM-P900 S Pen: correct the kernel experiment baseline

The original BOOT SHA-256 `7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14`
contains kernel **3.4.113-gde0cdcf1** from `exynos5420/android_kernel_samsung_exynos5420`
at `de0cdcf10dcca77b400f15d83c1edf4f264a0f02`, confirmed independently by its
embedded banner and the original build's locked manifest. The same pinned GCC
4.9 commit is `da10d2bd65e2c57d338fb6bb712ff522ad4e34e7`.

The earlier successful isolated zImage from run 42516456316 instead embeds
**3.4.113-g35d960ed-dirty** from a different kernel tree. Decoding the actual
LZMA kernel and its IKCONFIG reveals **93 changed/added/removed config symbols**.
This is not a single-variable comparison against the user's bootable kernel.
It must not be repacked into a BOOT as the next pen experiment.

The original and prior experimental images both use the legacy non-OF board
configuration and have zero appended bytes beyond the ARM zImage end. No DTB
was silently omitted; absence of appended bytes alone does not prove hardware
compatibility. Original kernel config SHA-256:
`cb9dfcd6c9ef9aaa0ad0b2243b90bf3c6184b3d8421b243247643e49900707fc`.

## Correction

- Retarget the existing one-line optional Wacom LCD-sync isolation to the exact
  original source, authenticating the entire original Wacom file SHA-256
  `72a7669ab02e62cf414444345b1e53333d63b3070d7f455fc4a4a5f6848477b6`.
- Seed the build from the configuration extracted from the actual original
  BOOT, not a different tree's defconfig. Use this 3.4 kernel's `oldnoconfig`
  target and reject any semantic config drift before compilation.
- Inspect the resulting compiled binary again: require original source banner
  and zero config differences before publishing a kernel artifact.
- Add bounded decompression and negative tests; no unbounded compressed input,
  duplicate config entries or unexplained appended kernel data is accepted.

Host suite after this change: **228 tests passed**. Actual archived BOOT/zImage
outer SHA-256 digests match GitHub's recorded artifact digests. Full decoded
comparison is in `r15-prior-isolation-baseline-mismatch-2026-11-10.json`.

The corrected kernel build is a source experiment. Successful compilation is
not proof of a fix for S Pen drawing freezes. No tablet writes or full Android
system rebuild are performed by this work. Physical drawing acceptance remains
FAIL for the previously installed ROM and NOT TESTED for the new experiment.

## Corrected compile and independent BOOT reconstruction

- Corrected compile [42909955707](https://github.com/elharika/ELHARIKA-OS-Lite/actions/runs/42909955707): SUCCESS.
- Corrected compiled zImage SHA-256: `8b920c96019869aa531b50fcad791b96f3aaf2d518bb4542883d1ce773379937`.
- Downloaded outer artifact SHA-256 `f42fa43bace6c571f3b5137afe7abf6f72fafc560d2fb2f508c2a393797df839` matches GitHub's digest.
- Actual compiled embedded config is byte-identical to the original config:
  `cb9dfcd6c9ef9aaa0ad0b2243b90bf3c6184b3d8421b243247643e49900707fc`.
  Semantic config differences: **ZERO**. Source banner: `3.4.113-gde0cdcf1-dirty`.
- Non-installable staging tooling preserves original ramdisk, board/cmdline,
  header load addresses and Samsung trailer; only kernel size and image ID change.
- Staged candidate BOOT SHA-256: `a4c0773787ccd9c4d1a4da592ebf204512f882717d76d23b6cf1411fb32b3022`.
- Both the original and new candidate were independently reconstructed using the
  **exact original mkbootimg source** pinned in the original build manifest:
  `LineageOS/android_system_tools_mkbootimg@ed76fccb92950d0d1fba31cc5777944a5a636c23`.
  Result: **byte-identical** for both. The legacy SHA-1 ID includes kernel,
  ramdisk, empty second stage and empty legacy DT lengths.
- Added staging regression tests: **233 host tests passed**.
- Staging archive contains candidate/original images, checksums and metadata;
  **no META-INF, TWRP update-binary or flashing command**. It is an engineering
  artifact, not a user installation update. Physical boot and drawing remain
  untested; no tablet writes were made.
