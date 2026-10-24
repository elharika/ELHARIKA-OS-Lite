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

The committed stock comparison found 141 of 150 exact paths. These bytes were inspected in an earlier run; the expanded stock image was subsequently removed by workspace maintenance. The new ELF scanner has been tested against generated ext4 fixtures, **not yet rerun against the stock image**. No new Mali, camera or audio ABI compatibility claim is made.

Next integration gates: recover stock image and run scanner; inspect alternative paths/versions for nine missing entries without silently substituting them; compare dependencies and symbols against the actual Android target output and linker namespaces; build system and boot image; perform physical boot, GPU and S Pen tests. A filename or matching architecture alone cannot satisfy these gates. Upstream provenance labels in the old report describe upstream requirements, not the origin of the extracted SM-P900 bytes.
