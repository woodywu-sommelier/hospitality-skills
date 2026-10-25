# Hospitality Skills MCP server

The three Hospitality Skills as tools that any MCP client can call: Claude Code, Claude Desktop, and other apps and agents that support the Model Context Protocol over stdio.

| Tool | Skill | What it does |
| --- | --- | --- |
| `audit_wine_list` | wine-list-audit | Ranked report on a wine list (and optional menu): Fix first, Worth a look, Fine as is, What's missing |
| `check_reply` | house-somm | Checks an assistant's reply against the venue's list: wines not on the list, wrong vintages or prices, tasting claims, missing hand-offs |
| `fact_guard` | wine-fact-guard | Flags likely fabrication in a wine answer, each flag with a reason and a source |

Every tool takes `format`: `markdown` (default, for people) or `json` (for programs).

**Runs entirely on your machine.** Python 3.11 or newer, standard library only: nothing to install, no network calls, no API keys. Your wine lists and replies never leave your computer.

## Set it up

First get the code:

```
git clone https://github.com/woodywu-sommelier/hospitality-skills
```

Then point your client at `mcp/server.py` inside that folder, using its full path.

**Claude Code**: the plugin installs the skills and these tools together:

```
/plugin marketplace add woodywu-sommelier/hospitality-skills
/plugin install hospitality-skills@hospitality-skills
```

Or add only the tools:

```
claude mcp add hospitality-skills -- python3 /full/path/to/hospitality-skills/mcp/server.py
```

**Claude Desktop**: open Settings, then Developer, then Edit Config, and add this to `claude_desktop_config.json`, then restart the app:

```json
{
  "mcpServers": {
    "hospitality-skills": {
      "command": "python3",
      "args": ["/full/path/to/hospitality-skills/mcp/server.py"]
    }
  }
}
```

**Other MCP clients**: add a stdio server with the command `python3` and the argument `/full/path/to/hospitality-skills/mcp/server.py`. On Windows, use `python` instead of `python3`.

## Try it

Once connected, ask your assistant something like:

- "Audit this wine list against our menu" (paste or attach both).
- "Check this reply against our list before I send it to the guest."
- "Run fact_guard on this answer about old Burgundy."

## How it works

`server.py` speaks JSON-RPC 2.0 over stdin and stdout, one message per line, and calls the same scripts as the skills, so results match the command-line tools exactly. Logs go to stderr. Protocol versions 2025-06-18, 2025-03-26 and 2024-11-05 are supported.

## Going further

- The House Somm, the hosted assistant that answers only from a venue's own list: [concierge.woodywusommelier.com](https://concierge.woodywusommelier.com)
- Service Audit for restaurants and hotels: [woodywusommelier.com/consulting/](https://woodywusommelier.com/consulting/)
- For AI Teams: [woodywusommelier.com/consulting/ai-teams/](https://woodywusommelier.com/consulting/ai-teams/)
