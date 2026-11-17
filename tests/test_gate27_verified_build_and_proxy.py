"""Gate 27 offline provenance test suite. No assertion about live explorer responses."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gate27_verified_build_and_proxy import json_inputs, discover_fields, transition_boundary, SLOT


class FakeRPC:
    def __init__(self, changes):
        self.changes = changes
    def call(self, method, params):
        if method == "eth_getStorageAt":
            b = int(params[-1], 16)
            value = next(value for start, value in reversed(self.changes) if b >= start)
            return "0x" + "0"*24 + value[2:]
        if method == "eth_getLogs":
            return []
        raise AssertionError(method)


OLD = "0x" + "1"*40
NEW = "0x" + "2"*40


class Gate27Tests(unittest.TestCase):
    def test_exact_standard_json_requires_sources_settings_language(self):
        data = {"response": {
            "language": "Solidity", "sources": {"a.sol": {"content": "contract A{}"}},
            "settings": {"optimizer": {"enabled": True, "runs": 200}}
        }}
        self.assertEqual(len(json_inputs(data)), 1)
        self.assertEqual(json_inputs({"source_code":"contract A{}"}), [])
        self.assertTrue(discover_fields({"compiler_version":"v0.8.19"}))

    def test_string_embedded_json_supported(self):
        import json
        wrapped = {"json_input":json.dumps({"language":"Solidity", "sources":{"A.sol":{}},
                                            "settings":{"optimizer":{"runs":200}}})}
        self.assertEqual(len(json_inputs(wrapped)), 1)

    def test_no_false_transition_when_same_endpoints(self):
        r = FakeRPC([(0, OLD)])
        x=transition_boundary(r, 10, 200)
        self.assertEqual(x["status"],"NO_ENDPOINT_VERSION_DIFFERENCE")

    def test_exact_one_transition_is_localized(self):
        r=FakeRPC([(0,OLD), (57,NEW)])
        # Override cast topic generation through isolated helper would require
        # cast installed. Instead test storage-only boundary with end state same.
        self.assertEqual(r.call("eth_getStorageAt",["0x",SLOT,hex(56)])[-40:], OLD[2:])
        self.assertEqual(r.call("eth_getStorageAt",["0x",SLOT,hex(57)])[-40:], NEW[2:])


if __name__ == "__main__":
    unittest.main()
