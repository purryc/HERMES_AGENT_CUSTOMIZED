# Mac Original AGENT Skill Sync

This repo syncs Mac skills from the original AGENT skill folders. Windows uses
the same idea and writes its original AGENT skills to `skills/windows-agent/`.

It does not assume skills are Codex-only, and it does not rewrite the skill
folders. The script copies source skill folders as-is when they contain
`SKILL.md` or `DESCRIPTION.md`.

## Daily Command

Run this at the end of the workday on the Mac:

```bash
cd hermes-memory
./scripts/sync-mac-to-github.sh
```

That command collects:

- Mac Codex memory from `~/.codex/memories` into `memory/mac-codex-memory.md`.
- Original AGENT skills into `skills/mac-agent/<hostname>/`.
- Project-level `AGENTS.md` files into `project-agents/<hostname>/`.

Then it pushes the safe allowlist to the private GitHub repo.

## Configure Original AGENT Skill Roots

Create a local config file:

```bash
cd hermes-memory
cp config/agent-skill-roots.example.txt config/agent-skill-roots.txt
```

Edit `config/agent-skill-roots.txt` to point at the real AGENT skill folders on
the Mac. Common examples:

```text
~/.agents/skills
~/AGENT/.agents/skills
~/AGENT/skills
~/.hermes/skills
```

You can also create a host-specific file:

```text
config/agent-skill-roots.<hostname>.txt
```

Host-specific config is useful if the work Mac and another Mac use different
folder layouts.

## Output Layout

Copied skills go here:

```text
skills/mac-agent/<hostname>/<source-root>/<skill-name>/
```

Example:

```text
skills/mac-agent/work-mac/HOME__AGENT__.agents__skills/my-skill/SKILL.md
```

The path includes the source root so two skill folders with the same skill name
do not overwrite each other.

## Safety Rules

The sync excludes common secret-bearing files and refuses to push if it sees
obvious API keys, bot tokens, passwords, or private keys.

Never store these in skills:

- `.env` or `.env.*`
- `auth.json`
- API keys or bot tokens
- Private keys
- Passwords or recovery codes

If the script blocks, read the printed file path, remove the secret from the
source skill folder, then run the command again.
