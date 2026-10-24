# Stock blob verification

`scripts/verify_stock_blobs.py` reads an expanded ext4 **system** image using debugfs without mounting or modifying it. It checks SM-P900/v1awifi identity and the baseline PDA, extracts the listed blobs into a temporary directory, compares SHA-256 hashes and inventories ELF architecture, DT_NEEDED dependencies and undefined dynamic symbols. No firmware binaries are uploaded or installed.

Requirements: Linux, Python 3, e2fsprogs, binutils. Tests additionally require a C compiler.

```sh
python3 -m unittest discover -s tests -p 'test_stock_blobs.py' -v
python3 scripts/verify_stock_blobs.py \
  --system-image /path/to/system.ext4 \
  --baseline reports/stock-P900XXS0BPL4-vendor-comparison.json \
  --report /path/to/stock-elf-inventory.json
```

Input must already be expanded ext4, not the stock ZIP, tar.md5 or Android sparse image. The tool does not change partitions or produce a flashable package. Exit 2 means at least one required path is missing or differs from the baseline; the report is still produced. Exit 0 means only all baseline files matched, not that Android can boot.

The stock ZIP was downloaded again and matched the pinned SHA-256. The scanner was then run on its expanded system image: **141 present files matched all 141 recorded hashes; nine exact required paths remain missing**. Exit 2 is expected. See `reports/stock-elf-summary.json` for actual DT_NEEDED lists, architecture and undefined-symbol counts.

Additional stock candidates found (not automatically substituted):

| Required path/version | Actual stock candidate | Status |
| --- | --- | --- |
| vendor/lib/libstlport.so | lib/libstlport.so | Different source path; runtime/symbol validation needed |
| bcm4350_V0301.0609.hcd | bcm4350_V0301.0591.hcd | Different firmware version; Bluetooth configuration and physical testing required |
| liblvverx_3.25.00.so | liblvverx_3.20.03.so | Different audio effect version; ABI/configuration checks required |
| liblvvetx_3.25.00.so | liblvvetx_3.20.03.so | Different audio effect version; ABI/configuration checks required |

Mali imports 11 shared libraries, including libui, libutils, libbinder and libstlport, and has 280 undefined dynamic symbols. libexynoscamera imports 20 libraries and has 341 undefined dynamic symbols. Undefined imports are normal for shared libraries; these counts are **not** missing-symbol counts. Resolution must be checked against the actual target Android binaries. Neither subsystem is yet proven compatible with Android 11.

`unpack_stock_system.py ZIP NEW_OUTPUT_DIRECTORY` reproduces extraction from the exact hash-pinned archive. It extracts only system.img, expands sparse chunks with bounds checks and refuses to overwrite an existing output directory. The pinned archive hash is checked; sparse CRC fields are not independently validated. Eight local fixture tests passed (four extraction/inventory tests and four sparse expansion tests).

Next integration gates: evaluate the recorded stock candidates and remaining missing entries without silently substituting them; compare dependencies and symbols against the actual Android target output and linker namespaces; build system and boot image; perform physical boot, GPU and S Pen tests. A filename or matching architecture alone cannot satisfy these gates. Upstream provenance labels in the old report describe upstream requirements, not the origin of the extracted SM-P900 bytes.
