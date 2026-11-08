import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/compare_sm_p900_uk_handshake_code.py"
spec = importlib.util.spec_from_file_location("sm_p900_handshake", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HandshakeSignatureTests(unittest.TestCase):
    def test_byte_offsets_match_only_when_all_four_instructions_align(self):
        patterns = {0: b"\x10\x20\x30\x40", 12: b"\x50\x60\x70\x80",
                    24: b"\x90\xa0\xb0\xc0", 40: b"\xd0\xe0\xf0\x01"}
        text = bytearray(b"\xff" * 110)
        for at, chunk in patterns.items():
            text[5 + at:5 + at + len(chunk)] = chunk
        self.assertEqual(m.exact_offset_matches(bytes(text), patterns), [5])
        text[5+24] = 0x2f
        self.assertEqual(m.exact_offset_matches(bytes(text), patterns), [])

    def test_invalid_signature_rejected(self):
        with self.assertRaises(ValueError):
            m.exact_offset_matches(b"foo", {})

    def test_proven_request_is_not_inferred_from_simple_matching(self):
        self.assertEqual(m.UK10_OPCODES[0], ("mov", "r0, #0xa"))
        self.assertEqual(m.UK10_OPCODES[0x18], ("strh", "r0, [sp, #4]"))
        self.assertNotEqual(m.DONOR_SHA256, m.KNOWN_UK10_SHA256)


if __name__ == "__main__":
    unittest.main()
