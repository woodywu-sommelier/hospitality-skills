# Submitting hospitality-skills

A short checklist for listing this plugin. Checked against the Claude Code and claude.com docs on 2026-10-26; check them again before you submit, because the portal's rules change.

## Before you submit

- [ ] Raise `version` in `.claude-plugin/plugin.json` (and in `marketplace.json` metadata) for every release. Users on an unchanged version keep their old copy. 0.2.0 is the first release with the fact guard's bottle-tied corrections and the newest known-facts entry.
- [ ] Run the tests: `python3 -m unittest discover -s tests`.
- [ ] Run the local checks from the repository root:
  - `claude plugin validate . --strict`
  - `claude plugin validate . --profile directory --strict` (the subset of directory checks the CLI can run, including the `icon` path)
- [ ] Confirm the listing fields in `plugin.json`: `icon` is `./assets/icon.png` (800x800 PNG), the documented form for an image inside the plugin. Optional extra listing fields the directory reads: `documentationUrl`, `supportUrl`, `privacyPolicyUrl`, `termsOfServiceUrl`, each an `https://` URL. Set these in `plugin.json` only, never in `marketplace.json`.
- [ ] Make sure the README describes everything the plugin runs, sends or fetches. The MCP server (`python3 ${CLAUDE_PLUGIN_ROOT}/mcp/server.py`) runs locally, and the scripts use the standard library only, with no network calls.
- [ ] No `.DS_Store`, `Thumbs.db`, `desktop.ini` or `__MACOSX` files, no Git LFS, no symlinks, no `.gitattributes` filters. Non-image files under 256 KiB, every file under 5 MiB, 512 files or fewer.
- [ ] Connect your GitHub account on claude.ai, in the organization you submit from. The portal checks that it can push to the repository. The repository must be public before the listing goes live (it is public now).

## Anthropic's plugin directory

1. You need a paid claude.ai plan (Pro or Max submit from your own account; on Team or Enterprise, an Owner submits). The listing belongs to the organization you submit from, so submit from the one that should own it long term.
2. Open the developer portal at <https://claude.ai/directory/manage> and select **Submit new**, then **Plugin bundle**.
3. On the **Source** step, enter `https://github.com/woodywu-sommelier/hospitality-skills`. Leave **Plugin path** empty (the plugin is at the repository root) and **Branch or tag** empty to follow the default branch.
4. Select **Validate**. Fix anything marked **Blocking**, push, then select **Re-validate**. A **Policy hold** means a reviewer reads it; you can still submit. The name `hospitality-skills` is made of generic words, so a reviewer hold on the name is possible.
5. **Listing details** shows the listing as read from `plugin.json` and the README. To change it, edit those files and validate again.
6. **Data handling**: the plugin itself stores or transmits nothing. Its scripts and local MCP server read only the text or files passed to them, write nothing to disk, make no network calls and keep nothing once they return, so there is no retention period. It does not ask for personal data. Claude still processes what the user sends in the conversation, as it does without the plugin. It is not intended for people under 18.
7. **Compliance**: check the contact email and select all four acknowledgements.
8. **Review and submit**: keep **GitHub push webhook** (you need admin access to the repository to set it up), then select **Submit for review**.
9. Each new commit on the tracked branch is scanned, including a security scan. A version that passes is not live until you select **Publish** on the plugin's page; by default a reviewer then publishes it.

Where it loads: skills load in claude.ai chat, Cowork and Claude Code. The local MCP server is ignored in chat, loads in Cowork when the session runs on your computer, and loads in Claude Code.

Reference: <https://claude.com/docs/plugins/submit>, <https://claude.com/docs/plugins/pre-submission-checklist>, <https://code.claude.com/docs/en/plugins/manifest-reference#directory-listing-fields>, and the [Anthropic Software Directory Policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy).

## Your own marketplace (already live)

`.claude-plugin/marketplace.json` already publishes the plugin from this repository; there is no form. Users install it with:

```
claude plugin marketplace add woodywu-sommelier/hospitality-skills
claude plugin install hospitality-skills@hospitality-skills
```

Anthropic's own marketplace, `claude-plugins-official`, does not take submissions through the portal.
