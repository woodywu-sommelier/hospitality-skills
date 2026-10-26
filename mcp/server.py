#!/usr/bin/env python3
"""Hospitality Skills MCP server: the three skills as tools for any MCP client.

Run it from an MCP client (Claude Code, Claude Desktop, or any client that
speaks MCP over stdio):

    python3 mcp/server.py

Tools:
    audit_wine_list   wine-list-audit: ranked report on a wine list (and menu)
    check_reply       house-somm: check an assistant's reply against the list
    fact_guard        wine-fact-guard: flag likely fabrication in a wine answer

Standard library only. Everything runs locally: no network, no API keys.
Messages are JSON-RPC 2.0, one per line on stdin and stdout; logs go to stderr.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
SERVER_INFO = {"name": "hospitality-skills", "title": "Hospitality Skills by Woody Wu",
               "version": "0.2.0"}
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")


def load_script(skill: str, module: str):
    """Import skills/<skill>/scripts/<module>.py by path (skill folders have dashes)."""
    scripts = SKILLS / skill / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    name = f"{skill.replace('-', '_')}_{module}"
    spec = importlib.util.spec_from_file_location(name, scripts / f"{module}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


audit = load_script("wine-list-audit", "audit_list")
reply_checker = load_script("house-somm", "check_reply")
winelist = load_script("house-somm", "winelist")
fact_guard = load_script("wine-fact-guard", "fact_guard")

FORMAT = {"type": "string", "enum": ["markdown", "json"], "default": "markdown",
          "description": "markdown for people, json for programs"}

TOOLS = [
    {
        "name": "audit_wine_list",
        "title": "Audit a wine list",
        "description": (
            "Audit a restaurant, bar or hotel wine list and return a short ranked report: Fix first, "
            "Worth a look, Fine as is, and what data was missing. Checks markups against Woody Wu's "
            "default bands (configurable; not industry rules), price ladder gaps, the second-cheapest "
            "bottle, the by-the-glass range, menu pairing coverage, duplicates, vintage and format "
            "oddities, and data problems. Never invents costs, prices or sales."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "wine_list": {"type": "string", "description": (
                    "The list as CSV or TSV with a header row (name, producer, region, grape, type, "
                    "vintage, format, cost, price, btg, glass_price), or plain text with one wine per "
                    "line and commas between fields.")},
                "menu": {"type": "string", "description": "Optional menu, one dish per line."},
                "title": {"type": "string", "description": "Venue name for the report heading."},
                "year": {"type": "integer", "description": "Current year for vintage checks."},
                "format": FORMAT,
            },
            "required": ["wine_list"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "check_reply",
        "title": "Check a wine assistant's reply",
        "description": (
            "Check a wine assistant's reply against the venue's own list. Flags any named wine not on "
            "the list, a wrong vintage or price, a list wine named without its vintage or price, "
            "first-person tasting claims, phrases that push drinking, and a missing hand-off to a "
            "person for allergies, faulty bottles or high-value bottles. A clean result means nothing "
            "was caught, not that the reply is perfect."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "wine_list": {"type": "string", "description": "The venue's list, CSV or plain text."},
                "reply": {"type": "string", "description": "The assistant's reply to check."},
                "guest_message": {"type": "string", "description": (
                    "Optional: the guest's message, used for allergy and faulty-bottle checks.")},
                "format": FORMAT,
            },
            "required": ["wine_list", "reply"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "fact_guard",
        "title": "Flag fabrication in a wine answer",
        "description": (
            "Review an AI-generated answer about wine and flag likely fabrication: phantom vintages "
            "from a curated, sourced list, false premises accepted as true, critic scores and "
            "quotations with no citation, provenance red flags treated as normal, and first-person "
            "tasting claims. Each flag has a reason and a source. This flags risk; it does not prove "
            "truth, and an empty result does not mean the answer is correct."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "description": "The answer to review."},
                "question": {"type": "string", "description": (
                    "Optional: the question it answers, used to catch accepted false premises.")},
                "format": FORMAT,
            },
            "required": ["answer"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
]


class ToolError(Exception):
    """A problem with the tool's input, reported to the model as a tool error."""


def _text(args: dict, key: str, required: bool = False) -> str:
    value = args.get(key)
    if value is None:
        if required:
            raise ToolError(f"Missing required argument: {key}")
        return ""
    if not isinstance(value, str):
        raise ToolError(f"Argument {key} must be a string")
    if required and not value.strip():
        raise ToolError(f"Argument {key} is empty")
    return value


def _format(args: dict) -> bool:
    value = args.get("format", "markdown")
    if value not in ("markdown", "json"):
        raise ToolError("format must be 'markdown' or 'json'")
    return value == "json"


def run_audit(args: dict) -> tuple[str, bool]:
    as_json = _format(args)
    year = args.get("year")
    if year is not None and not isinstance(year, int):
        raise ToolError("year must be an integer")
    menu = _text(args, "menu") or None
    text = audit.run(_text(args, "wine_list", required=True), menu, year=year,
                     title=_text(args, "title") or "wine list", as_json=as_json)
    return text, False


def run_check_reply(args: dict) -> tuple[str, bool]:
    as_json = _format(args)
    wines = winelist.parse_wine_list(_text(args, "wine_list", required=True)).wines
    if not wines:
        raise ToolError("No wines could be read from wine_list")
    flags, matches = reply_checker.check_reply(_text(args, "reply", required=True), wines,
                                               _text(args, "guest_message"))
    if as_json:
        data = {"flags": [asdict(f) for f in flags],
                "matched": [{k: v for k, v in asdict(m).items() if k not in ("start", "end")}
                            for m in matches]}
        return json.dumps(data, indent=2, ensure_ascii=False), False
    return reply_checker.render(flags, matches, len(wines)), False


def run_fact_guard(args: dict) -> tuple[str, bool]:
    as_json = _format(args)
    flags, confirmed = fact_guard.guard(_text(args, "answer", required=True), _text(args, "question"))
    if as_json:
        data = {"flags": [asdict(f) for f in flags], "handled_correctly": confirmed,
                "disclaimer": fact_guard.DISCLAIMER}
        return json.dumps(data, indent=2, ensure_ascii=False), False
    return fact_guard.render(flags, confirmed), False


HANDLERS = {"audit_wine_list": run_audit, "check_reply": run_check_reply, "fact_guard": run_fact_guard}


def call_tool(params: dict) -> dict:
    name = params.get("name")
    if name not in HANDLERS:
        raise LookupError(f"Unknown tool: {name}")
    args = params.get("arguments") or {}
    try:
        text, is_error = HANDLERS[name](args)
    except ToolError as exc:
        text, is_error = str(exc), True
    except Exception as exc:  # report, never crash the server
        print(traceback.format_exc(), file=sys.stderr)
        text, is_error = f"The tool failed: {exc}", True
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def handle(message: dict) -> dict | None:
    """Handle one JSON-RPC message; return the response, or None for notifications."""
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}
    if msg_id is None:
        return None
    try:
        if method == "initialize":
            requested = params.get("protocolVersion")
            version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
            result = {"protocolVersion": version, "capabilities": {"tools": {}},
                      "serverInfo": SERVER_INFO,
                      "instructions": ("Tools from Hospitality Skills by Woody Wu "
                                       "(woodywusommelier.com). Pass wine lists as CSV or plain "
                                       "text. Results flag risk; they are not proof.")}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            result = call_tool(params)
        else:
            return {"jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}}
    except LookupError as exc:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": str(exc)}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def serve(stdin=sys.stdin, stdout=sys.stdout) -> None:
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": "Parse error"}}
        else:
            if isinstance(message, list):
                responses = [r for r in (handle(m) for m in message if isinstance(m, dict)) if r]
                response = responses or None
            elif isinstance(message, dict):
                response = handle(message)
            else:
                response = {"jsonrpc": "2.0", "id": None,
                            "error": {"code": -32600, "message": "Invalid request"}}
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()


if __name__ == "__main__":
    serve()
