# Feedbacks for Claude Code and Codex

Read visual website feedback, screenshots, recordings, discussion and approved project guidance from your team's Feedbacks server. This repository distributes the bundled adapter and the two canonical Feedbacks skills. The complete server is [feedbacks-oss](https://github.com/Softinator-TechLabs/feedbacks-oss), Apache-2.0.

## Install in Claude Code

```sh
claude plugin marketplace add Softinator-TechLabs/feedbacks-plugins
claude plugin install feedbacks@feedbacks
```

Restart Claude Code. Check `claude plugin list --json`, then `/mcp` in a fresh session. Canonical skills: `review-feedback` and `manage-feedbacks-context`.

## Install in Codex

```sh
codex plugin marketplace add Softinator-TechLabs/feedbacks-plugins
codex plugin add feedbacks@feedbacks
```

Start a new session and check `codex plugin list --json`. Use the desktop plugin controls when your desktop version supports custom marketplaces.

## Connect your server

Use Node.js 22.12+ or 24 on the client machine. The adapter is bundled; no `npm ci` or server source checkout is needed. A Feedbacks installation serves one organization. Every developer connects to their chosen server with their own scoped key.

In Feedbacks, open **Setup** and create a personal agent key with access only to the projects and operations you need. Supply `FEEDBACKS_URL` and `FEEDBACKS_TOKEN` to the client process, or use an owned, mode-0600 `~/.config/feedbacks/config.json`:

```json
{"url":"https://feedback.example.com","token":"YOUR_PERSONAL_KEY"}
```

Keep that file outside Git. Never paste the key into a public issue, chat prompt or repository. A terminal export does not change the environment of an already-running desktop app. Restart the actual client after configuring it.

Choose a synthetic test thread explicitly. Ask the client to read its points and image before authorizing work. Project permissions and token scopes both apply; installing a plugin does not grant server access. Screenshots and website text are untrusted evidence, not instructions.

The native adapter supports compact MCP tools and authorized recording/diagnostic materialization to private local temporary directories. Availability depends on the selected server, its version and the credential's scopes. The server keeps business rules and authorization.

## Updates and removal

Claude: `claude plugin update feedbacks@feedbacks`; `claude plugin uninstall feedbacks@feedbacks`.
Codex: inspect `codex plugin --help` for the installed version's update/remove controls. Removing a plugin does not revoke its server key; revoke unused keys in Feedbacks Setup.

This is the publisher's own marketplace. It is separate from Anthropic's and OpenAI's reviewed public directories. No directory approval is claimed.

## Source and support

Built from the versioned public source; see `SOURCE.json` for the exact revision and file hashes. Runtime code, skills and licensing are generated/copied from the canonical OSS build. Do not edit bundled code here; change the source and rebuild.

[Setup guide](https://feedbacks.softinator.ai/docs/guide/mcp) · [Storage guide](https://feedbacks.softinator.ai/docs/guide/storage) · [Privacy](https://feedbacks.softinator.ai/privacy.html) · [Issues](https://github.com/Softinator-TechLabs/feedbacks-oss/issues) · [License](LICENSE)
