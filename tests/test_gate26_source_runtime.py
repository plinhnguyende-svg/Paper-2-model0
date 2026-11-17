"""Offline unit tests for Gate 26 comparison; synthetic bytecodes only."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gate26_source_runtime_audit import split_metadata, comparison, first_diff, parse_code


def make_runtime(prefix, metadata_hex="a1646970667342abcd"):
    meta = bytes.fromhex(metadata_hex)
    return prefix + meta + len(meta).to_bytes(2, "big")


class Gate26BytecodeTests(unittest.TestCase):
    def test_exact_match(self):
        original = make_runtime(b"\x60\x00\x56")
        self.assertEqual(comparison(original, original)["status"], "EXACT_RUNTIME_MATCH")

    def test_metadata_only_difference(self):
        a = make_runtime(b"\x60\x00\x56", "a1646970667342abcd")
        b = make_runtime(b"\x60\x00\x56", "a1646970667342abce")
        self.assertEqual(comparison(a, b)["status"],
                         "EXECUTABLE_PREFIX_MATCH_METADATA_DIFFERS")
        self.assertEqual(split_metadata(a)[0], b"\x60\x00\x56")

    def test_executable_difference_rejected(self):
        a = make_runtime(b"\x60\x00\x56")
        b = make_runtime(b"\x60\x01\x56")
        self.assertEqual(comparison(a, b)["status"], "EXECUTABLE_MISMATCH")
        self.assertEqual(first_diff(a, b), 1)

    def test_unrecognized_metadata_never_blindly_dropped(self):
        bad = b"\x60\x00\xff\xff\x00\x03"
        self.assertEqual(split_metadata(bad)[1], None)
        self.assertEqual(comparison(bad, bad[:-1] + b"\x02")["status"],
                         "RUNTIME_MISMATCH_METADATA_UNRESOLVED")

    def test_linkage_requires_proof(self):
        a = make_runtime(b"\x60\x00")
        self.assertEqual(comparison(a, a, unresolved_links=True)["status"],
                         "UNRESOLVED_LINK_OR_IMMUTABLE_REFERENCES")

    def test_parse_code(self):
        self.assertEqual(parse_code("0x1234"), bytes.fromhex("1234"))
        with self.assertRaises(ValueError):
            parse_code("0x__$unresolved$__")
        with self.assertRaises(ValueError):
            parse_code("nothex")


if __name__ == "__main__":
    unittest.main()
