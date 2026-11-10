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
