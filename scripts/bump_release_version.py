"""Bump the lockstep release version across marketplace, plugins, and skills.

Usage: python scripts/bump_release_version.py <old> <new>
"""

import json
import pathlib
import re
import sys

OLD, NEW = sys.argv[1], sys.argv[2]
root = pathlib.Path(__file__).resolve().parent.parent
changed = []

mp = root / ".claude-plugin" / "marketplace.json"
data = json.loads(mp.read_text(encoding="utf-8"))
if data["metadata"]["version"] != OLD:
    sys.exit(
        f"error: {mp.relative_to(root)} metadata.version is "
        f'"{data["metadata"]["version"]}", expected "{OLD}"; nothing modified.'
    )

text = mp.read_text(encoding="utf-8").replace(f'"version": "{OLD}"', f'"version": "{NEW}"')
mp.write_text(text, encoding="utf-8")
changed.append(mp)

plugin_count = 0
for pj in root.glob("plugins/*/.claude-plugin/plugin.json"):
    text = pj.read_text(encoding="utf-8")
    if f'"version": "{OLD}"' in text:
        pj.write_text(text.replace(f'"version": "{OLD}"', f'"version": "{NEW}"'), encoding="utf-8")
        changed.append(pj)
        plugin_count += 1

skill_count = 0
for sk in root.glob("plugins/*/skills/*/SKILL.md"):
    text = sk.read_text(encoding="utf-8")
    new_text = re.sub(
        rf"^version: {re.escape(OLD)}$", f"version: {NEW}", text, count=1, flags=re.MULTILINE
    )
    if new_text != text:
        sk.write_text(new_text, encoding="utf-8")
        changed.append(sk)
        skill_count += 1

for path in changed:
    print("bumped:", path.relative_to(root))
print(f"total: {len(changed)} files {OLD} -> {NEW}")

if plugin_count == 0:
    print(f'warning: no plugin.json files contained version "{OLD}"', file=sys.stderr)
if skill_count == 0:
    print(f'warning: no SKILL.md files contained version "{OLD}"', file=sys.stderr)
if plugin_count == 0 or skill_count == 0:
    sys.exit(1)
