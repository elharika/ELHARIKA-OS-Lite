#!/usr/bin/env python3
"""Non-flashing disassembly around real SM-P900 UK10 Mali eglSwapBuffers fault.

Only exact SHA pinned upstream candidate source may be decoded. Emits a small
instruction window and ELF symbol/address checks, never a proprietary binary.
"""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE_SHA256 = "a66179ef65c26a797b814e3d9cf0ab2b7f07e0d32c641f463820c0a0c49f1ee9"
CRASH_PC = 0x263458
FAULT_SYMBOL = "eglp_swap_buffers"
FAULT_OFFSET = 1460


def audit(path):
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Unknown candidate Mali blob. No fixed-offset disassembly.")
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
    from elftools.elf.elffile import ELFFile
    with path.open("rb") as f:
        elf = ELFFile(f)
        if elf.elfclass != 32 or not elf.little_endian or elf["e_machine"] != "EM_ARM":
            raise ValueError("Not ARM32 Mali ELF")
        section = elf.get_section_by_name(".text")
        if section is None:
            raise ValueError("No ELF .text section")
        base, data = int(section["sh_addr"]), section.data()
        if not base + 24 <= CRASH_PC < base + len(data) - 24:
            raise ValueError("Crash PC outside executable text")
        symbols = {}
        for tab_name in (".symtab", ".dynsym"):
            symtab = elf.get_section_by_name(tab_name)
            if symtab is None:
                continue
            for sym in symtab.iter_symbols():
                if sym.name == FAULT_SYMBOL:
                    symbols[tab_name] = int(sym["st_value"])
        off = CRASH_PC - base
        start = off - 24
        end = off + 28
        decoder = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        instructions = list(decoder.disasm(data[start:end], base + start))
        if not any(x.address == CRASH_PC for x in instructions):
            raise ValueError("No decoded instruction at the fault address")
        # Use at most 13 instructions; the raw candidate binary is never shared.
        output = [{"pc": f"0x{x.address:08x}", "opcode": x.mnemonic,
                   "operands": x.op_str, "at_fault": x.address == CRASH_PC}
                  for x in instructions[:13]]
        matching_symbols = {name: address
                            for name, address in symbols.items()
                            if address + FAULT_OFFSET == CRASH_PC}
        return {
            "status": "PINNED_UK10_EGL_SWAP_DISASSEMBLY_ONLY",
            "source_sha256": digest,
            "real_device_crash_pc": f"0x{CRASH_PC:08x}",
            "reported_symbol": FAULT_SYMBOL,
            "reported_symbol_offset": FAULT_OFFSET,
            "symbol_match": matching_symbols,
            "instructions": output,
            "cause_proven": False,
            "hardware_fixed": False,
            "flash_approved": False,
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("candidate", type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    result = audit(a.candidate)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
