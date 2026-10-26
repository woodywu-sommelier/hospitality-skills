# Submitting hospitality-skills

A short checklist for listing this plugin. Checked against the Claude Code and claude.com docs on 2026-10-26; check them again before you submit, because the portal's rules change.

## Before you submit

- [ ] Raise `version` in `.claude-plugin/plugin.json` (and in `marketplace.json` metadata) for every release. Users on an unchanged version keep their old copy.
- [ ] Run the tests: `python3 -m unittest discover -s tests`.
- [ ] Run the local checks from the repository root:
  - `claude plugin validate . --strict`
  - `claude plugin validate . --profile directory --strict` (the subset of directory checks the CLI can run)
- [ ] Confirm the listing fields in `plugin.json`: `icon` is `./assets/icon.png` (800x800 PNG). Optional extra listing fields the directory reads: `documentationUrl`, `supportUrl`, `privacyPolicyUrl`, `termsOfServiceUrl`, each an `https://` URL.
- [ ] Make sure the README describes everything the plugin runs, sends or fetches. The MCP server (`python3 ${CLAUDE_PLUGIN_ROOT}/mcp/server.py`) runs locally and the scripts use the standard library only.
- [ ] No `.DS_Store`, `Thumbs.db` or `__MACOSX` files, no Git LFS, no symlinks. Non-image files under 256 KiB, 512 files or fewer.

## Anthropic's plugin directory

1. You need a paid claude.ai plan (Pro or Max submit from your own account; on Team or Enterprise, an Owner submits).
2. Open the developer portal at <https://claude.ai/directory/manage> and select **Submit new**, then **Plugin bundle**.
3. On the **Source** step, enter `https://github.com/woodywu-sommelier/hospitality-skills` (the plugin is at the repository root).
4. Select **Validate**. Fix anything marked **Blocking**, push, then select **Re-validate**. A **Policy hold** means a reviewer reads it; you can still submit.
5. Submit. After submitting, each new commit on the followed branch is scanned, including a security scan.

Where it loads: skills load in claude.ai chat, Cowork and Claude Code. The local MCP server is ignored in chat, loads in Cowork when the session runs on your computer, and loads in Claude Code.

Reference: <https://claude.com/docs/plugins/submit>, <https://claude.com/docs/plugins/pre-submission-checklist>, and the [Anthropic Software Directory Policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy).

## Your own marketplace (already live)

`.claude-plugin/marketplace.json` already publishes the plugin from this repository; there is no form. Users install it with:

```
claude plugin marketplace add woodywu-sommelier/hospitality-skills
claude plugin install hospitality-skills@hospitality-skills
```

Anthropic's own marketplace, `claude-plugins-official`, does not take submissions through the portal.
