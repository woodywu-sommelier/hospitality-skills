import json
import subprocess
import sys
import unittest

from helpers import ROOT, SKILLS

SERVER = ROOT / "mcp" / "server.py"


def session(*messages):
    """Run the server over stdio with these messages; return responses by id."""
    text = "\n".join(json.dumps(m) for m in messages) + "\n"
    proc = subprocess.run([sys.executable, str(SERVER)], input=text, capture_output=True,
                          text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return {r["id"]: r for r in map(json.loads, proc.stdout.splitlines())}


def init(version="2025-06-18"):
    return {"jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": version, "capabilities": {},
                       "clientInfo": {"name": "test", "version": "0"}}}


def call(msg_id, name, **arguments):
    return {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}}


class McpServerTests(unittest.TestCase):
    def test_initialize_and_list_tools(self):
        out = session(init(), {"jsonrpc": "2.0", "method": "notifications/initialized"},
                      {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(out[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", out[0]["result"]["capabilities"])
        names = [t["name"] for t in out[1]["result"]["tools"]]
        self.assertEqual(names, ["audit_wine_list", "check_reply", "fact_guard"])
        for tool in out[1]["result"]["tools"]:
            self.assertEqual(tool["inputSchema"]["type"], "object")
        self.assertEqual(len(out), 2, "notifications must not get a response")

    def test_older_and_unknown_protocol_versions(self):
        self.assertEqual(session(init("2024-11-05"))[0]["result"]["protocolVersion"], "2024-11-05")
        self.assertEqual(session(init("1999-01-01"))[0]["result"]["protocolVersion"], "2025-06-18")

    def test_tools_match_the_command_line_scripts(self):
        list_text = (SKILLS / "wine-list-audit" / "examples" / "bistro-lanterne-list.txt").read_text("utf-8")
        expected = (SKILLS / "wine-list-audit" / "examples" / "bistro-lanterne-expected-report.md").read_text("utf-8")
        out = session(init(), call(1, "audit_wine_list", wine_list=list_text, year=2026,
                                   title="Bistro Lanterne (fictional)"))
        self.assertEqual(out[1]["result"]["content"][0]["text"], expected)
        self.assertFalse(out[1]["result"]["isError"])

    def test_check_reply_and_fact_guard(self):
        copper = (SKILLS / "house-somm" / "examples" / "copper-fig-list.csv").read_text("utf-8")
        out = session(init(),
                      call(1, "check_reply", wine_list=copper, reply="Try the Domaine Hors-Liste 2015.",
                           format="json"),
                      call(2, "fact_guard", answer="The 1948 Romanée-Conti is superb.", format="json"))
        flags = json.loads(out[1]["result"]["content"][0]["text"])["flags"]
        self.assertIn("not_on_list", [f["kind"] for f in flags])
        guard = json.loads(out[2]["result"]["content"][0]["text"])
        self.assertIn("phantom_vintage", [f["category"] for f in guard["flags"]])
        self.assertIn("does not prove truth", guard["disclaimer"])

    def test_bad_input_is_a_tool_error_not_a_crash(self):
        out = session(init(), call(1, "audit_wine_list"), call(2, "fact_guard", answer="x", format="pdf"),
                      call(3, "check_reply", wine_list="", reply="hi"),
                      {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope"}},
                      {"jsonrpc": "2.0", "id": 5, "method": "no/such/method"})
        for msg_id in (1, 2, 3):
            self.assertTrue(out[msg_id]["result"]["isError"], msg_id)
        self.assertEqual(out[4]["error"]["code"], -32602)
        self.assertEqual(out[5]["error"]["code"], -32601)

    def test_ping_and_parse_error(self):
        proc = subprocess.run([sys.executable, str(SERVER)],
                              input='{"jsonrpc":"2.0","id":9,"method":"ping"}\nnot json\n',
                              capture_output=True, text=True, timeout=60)
        lines = [json.loads(l) for l in proc.stdout.splitlines()]
        self.assertEqual(lines[0], {"jsonrpc": "2.0", "id": 9, "result": {}})
        self.assertEqual(lines[1]["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
