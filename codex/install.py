#!/usr/bin/env python3
"""Install the power-bi-agentic-dev skills into OpenAI Codex.

Projects the Claude Code plugin skills in this repo into Codex's skill
discovery location (default: ~/.agents/skills) and installs the AGENTS.md
adapter block into the Codex home (default: ~/.codex, honors $CODEX_HOME).
The repo itself is never modified; the clone remains the runtime store for
scripts, binaries, and reviewer-agent checklists.

Usage:
    python codex/install.py                  install skills + AGENTS.md block
    python codex/install.py --check          dry run: report what would happen
    python codex/install.py --mcp            also merge MCP servers into config.toml
    python codex/install.py --mode junction  link instead of copy (auto-updates on git pull)
    python codex/install.py --project DIR    install into DIR/.agents/skills (project scope)
    python codex/install.py --uninstall      remove everything this script installed

Notes:
    - copy mode rewrites ${CLAUDE_PLUGIN_ROOT} in the copies to the absolute
      plugin path inside this clone, so bundled scripts and binaries resolve.
    - junction mode (Windows directory junction / POSIX symlink) tracks the
      repo live; ${CLAUDE_PLUGIN_ROOT} is left as-is and explained by the
      AGENTS.md adapter instead.
    - Skills list context budget in Codex is ~2% of the context window
      (8,000 chars when unknown); --check reports total description size.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CODEX_DIR = REPO / "codex"

PLUGIN_ROOT_TOKEN = b"${CLAUDE_PLUGIN_ROOT}"
SENTINEL_BEGIN = "<!-- pbi-agentic-dev:begin -->"
SENTINEL_END = "<!-- pbi-agentic-dev:end -->"
TOML_BEGIN = "# >>> pbi-agentic-dev >>>"
TOML_END = "# <<< pbi-agentic-dev <<<"
MANIFEST_NAME = ".pbi-agentic-dev-manifest.json"

# Skills that are functionally tied to Anthropic/Claude services and make no
# sense under Codex. Override with --include-all.
EXCLUDED_SKILLS = {"claude-design-handoff"}

# Codex shortens or omits skill descriptions past this budget (the documented
# fallback when the model's context window is unknown).
DESCRIPTION_BUDGET = 8000

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def log(msg: str) -> None:
    print(msg)


def warn(msg: str) -> None:
    print(f"  [!] {msg}")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    """Extract name/description from SKILL.md frontmatter (single-line values)."""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^(name|description|version)\s*:\s*(.*)$", line)
        if km:
            fields[km.group(1)] = km.group(2).strip().strip("\"'")
    return fields


def discover_skills(include_all: bool) -> list[dict]:
    """Enumerate plugin skills + codex command-skills. Returns dicts with
    name, description, source dir, and the plugin root for token rewriting."""
    skills: list[dict] = []
    seen: dict[str, Path] = {}

    def add(skill_dir: Path, plugin_root: Path, origin: str) -> None:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            return
        fm = parse_frontmatter(skill_md)
        name = fm.get("name") or skill_dir.name
        if not include_all and name in EXCLUDED_SKILLS:
            return
        if name in seen:
            fail(f"duplicate skill name '{name}' ({seen[name]} vs {skill_dir})")
        seen[name] = skill_dir
        skills.append(
            {
                "name": name,
                "description": fm.get("description", ""),
                "dir": skill_dir,
                "plugin_root": plugin_root,
                "origin": origin,
            }
        )

    for plugin_dir in sorted((REPO / "plugins").iterdir()):
        skills_root = plugin_dir / "skills"
        if not skills_root.is_dir():
            continue
        for skill_dir in sorted(skills_root.iterdir()):
            if skill_dir.is_dir():
                add(skill_dir, plugin_dir, plugin_dir.name)

    command_skills = CODEX_DIR / "command-skills"
    if command_skills.is_dir():
        for skill_dir in sorted(command_skills.iterdir()):
            if skill_dir.is_dir():
                add(skill_dir, CODEX_DIR, "codex-command")

    return skills


def tracked_files(skill_dir: Path) -> list[Path]:
    """Git-tracked files under skill_dir (keeps node_modules and other
    gitignored local artifacts out of the copies). Falls back to a walk."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z", "--", str(skill_dir.relative_to(REPO))],
            capture_output=True,
            check=True,
        ).stdout
        files = [REPO / p for p in out.decode("utf-8").split("\0") if p]
        if files:
            return files
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    skip = {"node_modules", "__pycache__", ".git"}
    result = []
    for root, dirs, names in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in skip]
        result.extend(Path(root) / n for n in names)
    return result


def copy_skill(skill: dict, dest: Path, prefix: str) -> None:
    """Copy tracked files, rewriting ${CLAUDE_PLUGIN_ROOT} to the clone's
    plugin path and (optionally) prefixing the frontmatter name."""
    plugin_root_posix = skill["plugin_root"].as_posix().encode("utf-8")
    for src in tracked_files(skill["dir"]):
        rel = src.relative_to(skill["dir"])
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        if PLUGIN_ROOT_TOKEN in data:
            data = data.replace(PLUGIN_ROOT_TOKEN, plugin_root_posix)
        if prefix and rel == Path("SKILL.md"):
            text = data.decode("utf-8")
            text = re.sub(
                r"^name\s*:\s*(.+)$",
                lambda m: f"name: {prefix}{m.group(1).strip()}",
                text,
                count=1,
                flags=re.MULTILINE,
            )
            data = text.encode("utf-8")
        target.write_bytes(data)
        shutil.copystat(src, target, follow_symlinks=False)


def make_junction(src: Path, dst: Path) -> None:
    if os.name == "nt":
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            fail(f"mklink /J failed for {dst}: {r.stderr.strip() or r.stdout.strip()}")
    else:
        os.symlink(src, dst, target_is_directory=True)


def remove_installed(path: Path, mode: str) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if mode == "junction":
        # os.rmdir removes a junction/symlink without touching its target.
        if path.is_symlink():
            path.unlink()
        else:
            os.rmdir(path)
    else:
        if not (path / "SKILL.md").is_file():
            warn(f"refusing to remove {path} (no SKILL.md — not a skill dir?)")
            return
        shutil.rmtree(path)


def load_manifest(target: Path) -> dict | None:
    mf = target / MANIFEST_NAME
    if mf.is_file():
        return json.loads(mf.read_text(encoding="utf-8"))
    return None


def render_agents_block(skills_dir: Path) -> str:
    template = (CODEX_DIR / "AGENTS-pbi.md").read_text(encoding="utf-8")
    body = template.replace("{{REPO}}", REPO.as_posix()).replace(
        "{{SKILLS_DIR}}", skills_dir.as_posix()
    )
    return f"{SENTINEL_BEGIN}\n{body.strip()}\n{SENTINEL_END}\n"


def upsert_block(file: Path, block: str, begin: str, end: str) -> str:
    """Insert or replace the sentinel-delimited block in file. Returns action."""
    if file.is_file():
        text = file.read_text(encoding="utf-8")
        if begin in text and end in text:
            pre, rest = text.split(begin, 1)
            _, post = rest.split(end, 1)
            file.write_text(pre + block.rstrip("\n") + post, encoding="utf-8")
            return "updated"
        sep = "" if (not text or text.endswith("\n\n")) else ("\n" if text.endswith("\n") else "\n\n")
        file.write_text(text + sep + block, encoding="utf-8")
        return "appended"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(block, encoding="utf-8")
    return "created"


def strip_block(file: Path, begin: str, end: str) -> bool:
    if not file.is_file():
        return False
    text = file.read_text(encoding="utf-8")
    if begin not in text or end not in text:
        return False
    pre, rest = text.split(begin, 1)
    _, post = rest.split(end, 1)
    merged = pre.rstrip("\n")
    post = post.lstrip("\n")
    new = (merged + "\n\n" + post if merged and post else merged + post).strip("\n")
    file.write_text((new + "\n") if new else "", encoding="utf-8")
    return True


def routing_table_coverage(skills: list[dict]) -> list[str]:
    """Skill names missing from the AGENTS-pbi.md routing table (drift check)."""
    template = (CODEX_DIR / "AGENTS-pbi.md").read_text(encoding="utf-8")
    return [s["name"] for s in skills if f"`{s['name']}`" not in template]


def cmd_check(skills: list[dict], target: Path, prefix: str) -> None:
    log(f"repo:   {REPO}")
    log(f"target: {target}")
    log(f"skills: {len(skills)} to install "
        f"({sum(1 for s in skills if s['origin'] == 'codex-command')} command-skills, "
        f"excluded by default: {', '.join(sorted(EXCLUDED_SKILLS))})")

    total_desc = sum(len(s["description"]) for s in skills)
    log(f"\ndescription budget: {total_desc:,} chars total "
        f"(Codex fallback budget {DESCRIPTION_BUDGET:,}; may shorten if over — "
        f"the AGENTS.md routing table is the backstop)")
    for s in sorted(skills, key=lambda x: -len(x["description"]))[:5]:
        log(f"    {len(s['description']):>5}  {s['name']}")

    missing = routing_table_coverage(skills)
    if missing:
        warn(f"not in AGENTS-pbi.md routing table (update it): {', '.join(missing)}")

    collisions = []
    for s in skills:
        dest = target / f"{prefix}{s['name']}"
        if dest.exists():
            manifest = load_manifest(target)
            ours = manifest and f"{prefix}{s['name']}" in manifest.get("skills", [])
            collisions.append((dest, "ours, will refresh" if ours else "FOREIGN — needs --force"))
    if collisions:
        log("\nexisting targets:")
        for dest, status in collisions:
            log(f"    {dest.name}: {status}")
    log("\ncheck complete (nothing written).")


def cmd_uninstall(target: Path, codex_home: Path) -> None:
    manifest = load_manifest(target)
    if not manifest:
        fail(f"no manifest at {target / MANIFEST_NAME} — nothing to uninstall")
    mode = manifest.get("mode", "copy")
    for name in manifest.get("skills", []):
        remove_installed(target / name, mode)
        log(f"  removed {name}")
    agents_md = Path(manifest.get("agents_md") or codex_home / "AGENTS.md")
    if strip_block(agents_md, SENTINEL_BEGIN, SENTINEL_END):
        log(f"  removed AGENTS.md block from {agents_md}")
    config_toml = Path(manifest.get("config_toml") or codex_home / "config.toml")
    if strip_block(config_toml, TOML_BEGIN, TOML_END):
        log(f"  removed MCP block from {config_toml}")
    (target / MANIFEST_NAME).unlink()
    log("uninstall complete.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["copy", "junction"], default="copy")
    ap.add_argument("--target", type=Path, default=None,
                    help="skills dir (default: ~/.agents/skills)")
    ap.add_argument("--project", type=Path, default=None,
                    help="install into PROJECT/.agents/skills instead of user scope")
    ap.add_argument("--codex-home", type=Path,
                    default=Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser(),
                    help="where AGENTS.md/config.toml live (default: $CODEX_HOME or ~/.codex)")
    ap.add_argument("--prefix", default="", help="prefix for installed skill names (copy mode only)")
    ap.add_argument("--include-all", action="store_true",
                    help=f"also install excluded skills: {', '.join(sorted(EXCLUDED_SKILLS))}")
    ap.add_argument("--mcp", action="store_true", help="merge MCP servers into config.toml")
    ap.add_argument("--skip-agents-md", action="store_true")
    ap.add_argument("--force", action="store_true", help="replace foreign dirs at the target")
    ap.add_argument("--check", action="store_true", help="dry run")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()

    if args.project:
        target = args.project.expanduser().resolve() / ".agents" / "skills"
    else:
        target = (args.target or Path("~/.agents/skills")).expanduser()

    if args.uninstall:
        cmd_uninstall(target, args.codex_home)
        return

    if args.prefix and args.mode == "junction":
        fail("--prefix requires copy mode (junction cannot rewrite frontmatter)")

    skills = discover_skills(args.include_all)
    if not skills:
        fail("no skills found — run from a full clone of the repo")

    if args.check:
        cmd_check(skills, target, args.prefix)
        return

    target.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(target) or {}
    previously_ours = set(manifest.get("skills", []))
    prev_mode = manifest.get("mode", args.mode)

    installed: list[str] = []
    for s in skills:
        name = f"{args.prefix}{s['name']}"
        dest = target / name
        if dest.exists() or dest.is_symlink():
            if name in previously_ours:
                remove_installed(dest, prev_mode)
            elif args.force:
                remove_installed(dest, "copy")
            else:
                warn(f"skipping {name}: exists and not installed by this script (use --force)")
                continue
        if args.mode == "copy":
            copy_skill(s, dest, args.prefix)
        else:
            make_junction(s["dir"], dest)
        installed.append(name)
    log(f"installed {len(installed)} skills to {target} ({args.mode} mode)")

    # Anything we installed before that no longer exists upstream: clean up.
    for stale in sorted(previously_ours - set(installed)):
        if (target / stale).exists() or (target / stale).is_symlink():
            remove_installed(target / stale, prev_mode)
            log(f"  removed stale skill {stale}")

    agents_md = args.codex_home / "AGENTS.md"
    if not args.skip_agents_md:
        action = upsert_block(agents_md, render_agents_block(target), SENTINEL_BEGIN, SENTINEL_END)
        log(f"AGENTS.md block {action}: {agents_md}")

    config_toml = args.codex_home / "config.toml"
    if args.mcp:
        snippet = (CODEX_DIR / "config-snippets.toml").read_text(encoding="utf-8")
        block = f"{TOML_BEGIN}\n{snippet.strip()}\n{TOML_END}\n"
        action = upsert_block(config_toml, block, TOML_BEGIN, TOML_END)
        log(f"MCP config block {action}: {config_toml}")

    total_desc = sum(len(s["description"]) for s in skills)
    if total_desc > DESCRIPTION_BUDGET:
        warn(f"total skill descriptions = {total_desc:,} chars (> {DESCRIPTION_BUDGET:,} fallback "
             f"budget); Codex may shorten them — the AGENTS.md routing table covers the gap")
    missing = routing_table_coverage(skills)
    if missing:
        warn(f"skills missing from AGENTS-pbi.md routing table: {', '.join(missing)}")

    (target / MANIFEST_NAME).write_text(
        json.dumps(
            {
                "repo": str(REPO),
                "mode": args.mode,
                "prefix": args.prefix,
                "skills": installed,
                "agents_md": None if args.skip_agents_md else str(agents_md),
                "config_toml": str(config_toml) if args.mcp else None,
                "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    log("done. Restart Codex (or start a session) and run /skills to verify.")


if __name__ == "__main__":
    main()
