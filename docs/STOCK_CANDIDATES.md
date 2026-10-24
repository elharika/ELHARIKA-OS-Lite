# Original SM-P900 candidate set — not runtime validated

Actual static analysis of P900XXS0BPL4 libraries found:

| Library | Strong imports | Not found in direct stock dependency exports |
| --- | ---: | ---: |
| Mali | 280 | 0 |
| Exynos camera | 341 | 0 |
| NXP receive effect 3.20.03 | 39 | 0 |
| NXP transmit effect 3.20.03 | 39 | 0 |
| STLport | 106 | 0 |

The stock STLport provides 29 symbols imported by Mali. Both effect libraries export AELI. These are STOCK-to-STOCK exact-name comparisons, **not Android 11 linkage tests**. The scanner does not emulate linker namespaces, global/transitive resolution, relocations or symbol-version binding.

Binary inspection also found the configured effect UUID structures in the original ARM little-endian libraries: receive lmfv at file offset 430100 and fens at 430444; transmit AGC at 536768, AEC at 536596 and NS at 536940. This confirms identifiers occur in the files, not that their Android 11 effect ABI works.

An explicit experimental override set now selects four files from this exact SM-P900 stock image: lib/libstlport.so; bcm4350_V0301.0591.hcd; liblvverx_3.20.03.so; liblvvetx_3.20.03.so. Original stock SHA-256/SHA-1 values are recorded in rom/stock-candidate-overrides.json. Bluetooth retains its actual .0591 filename; no firmware version renaming is performed. Audio destination filenames follow the previously audited effect library names.

```sh
python3 scripts/stock_candidate_baseline.py MINIMAL_BASELINE.json NEW_CANDIDATE_BASELINE.json
python3 scripts/stage_stock_vendor.py --system-image SYSTEM.ext4 \
  --baseline NEW_CANDIDATE_BASELINE.json --output NEW_CANDIDATE_STAGE
```

This was executed against the stock image: 143 distinct files staged, all SHA-256 checks passed, no absent entries in this experimental list. It is still INCOMPLETE_NOT_FLASHABLE. No candidates have been marked runtime-compatible or integrated into a released ROM. A zero missing-file count only establishes source availability.

Remaining work includes generating vendor build modules from the candidate list, adapting original blob fixups, validating the source-built libaudioroute, compiling Android, resolving Android 11 symbols/namespaces and SELinux, controller firmware selection, effect ABI tests, GPU/camera/pen tests and packaging. Original upstream version pins are retained as evidence and do not match these candidate replacements.

Generated extraction lists are committed under `rom/stock-candidate-lists/` for the three audited device trees. Reproduce them with `python3 scripts/export_candidate_lists.py CANDIDATE_BASELINE.json NEW_LIST_DIRECTORY`. They pin the actual source bytes, preserve the real Bluetooth filename and omit aptX/Widevine. They are not installed into upstream trees automatically and do not generate vendor build modules by themselves. Upstream extraction scripts contain blob fixups that still require review against these stock versions before use.
