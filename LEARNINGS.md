# Learnings: where a new fact goes

Skills in this marketplace are written from experience. When an agent discovers something the
skill does not say, that discovery has to land somewhere it will still be read months later, on a
different machine, by someone else.

This file is the canonical statement of where. The block between the sentinels below is copied
verbatim into the three SKILL.md files that instruct an agent to record learnings
(`fabric-cli`, `connect-pbid`, `pbir-cli`). `scripts/check-skill-hygiene.py` fails if the copies
drift, so edit this file and re-sync rather than editing a copy.

## Why this exists

Four files on one Windows PC accumulated about a year of verified Power BI knowledge:
`~/.claude/rules/{tmdl-pbir-authoring,fabric-cli,pbir-cli,connect-pbid}.md`. They held the TMDL
indentation rule that silently deletes format strings, the PBIR extension-measure tag that makes a
published report error per visual, the gateway-free Fabric refresh recipe, and around a hundred
other things learned by breaking something first.

None of it travelled. Not to a Codespace, not to a second machine, not to anyone else running these
plugins. Every one of those facts is now in the skill that owns its topic. The rule below is what
keeps the next hundred from ending up in the same dead end.

<!-- boundary-rule:begin -->
## Where a new learning goes

Three questions, in order. Stop at the first yes.

**1. Is it true only because of how THIS machine is set up right now?**
An installed path, which identity you are logged in as, a preview toggle, a console codepage, which
build happens to be installed. Then it is machine-local.

Before accepting that answer, try to generalise it. Most machine-local facts are the residue of a
search that succeeded once, and the search is the portable part:

| Instead of recording | Record |
| --- | --- |
| the path where you found a DLL | the probe that finds it, and how to tell which host can load it |
| that a preview toggle is off here | the verbatim symptom string, and the route that works regardless |
| which account has rights here | the check that reveals the mismatch |
| that a script cannot find a binary | a fix to the script |

If the generalised form survives, it is not machine-local: take it to question 2 or 3. If nothing
survives, because the fact is about one machine, one tenant or one person, write it to the agent's
own memory file and nowhere else. It would mislead an agent anywhere else, and this repository is
public.

**A Codespace has no legitimate machine-local layer.** A fact about a Codespace is true of every
Codespace built from the same devcontainer, which makes it a fact about that image. Commit it.
Never start a memory file inside a container.

**2. Is it true only where Power BI Desktop runs, only in a Windows shell, or only at some tool
version?**
Then it is portable knowledge with a boundary. It goes in this skill's `references/`, with the
boundary in the sentence:

- Platform: open or close with the scope. "On a cp1252 Windows console ... Linux and macOS never
  hit this." "Power BI Desktop only."
- Version: write the symptom and the check as the instruction, never the version. "If `fab find`
  errors, run `fab --version` before assuming a syntax problem." Put the version and date you
  observed in brackets at the end, never in the imperative. A version in the imperative rots into a
  lie; a version in brackets rots into a footnote.
- A dated or version-pinned claim also carries a `Retest:` line naming the one command that settles
  it, plus a `Verified <date>` stamp. `scripts/check-skill-hygiene.py` reports the stale ones and
  fails on a version claim with no `Retest:`.

**A scoped statement that is a ROUTE is not finished until it names the substitute in the same
sentence.** "`pbir desktop screenshot` is Windows and Desktop only" leaves a Linux agent stuck.
"`pbir desktop screenshot` is Windows and Desktop only; where Desktop is unavailable, render
server-side with the `ExportTo` API (fabric-cli `references/reports.md`)" does not.

**3. Otherwise it is a fact about the file format, the product, or the service API.**
True everywhere, including a Codespace with no Desktop and no Windows. It goes in this skill's
`references/` with no qualifier, or in `SKILL.md` when the agent must know it before opening any
reference. This is the default and where most learnings land.

### Two tests that settle almost every case

- *Would this sentence still be true in a Linux Codespace with no Power BI Desktop?* Yes means
  question 3. No, but only because Desktop is missing, means question 2. No, because the sentence
  names a path, a version or a toggle, means question 1, so run the generalisation table first.
- *Could anyone else running this plugin act on it?* If not, question 1.

### When torn, file it in the more public place

An over-cautious scope clause on a portable fact costs a reader one clause. A machine-local fact
shipped as product knowledge misleads everyone who installs the plugin.

### Where to write it

If `PBI_MARKETPLACE_ROOT` is set, a writable clone of this marketplace is on the machine:
`bash "$PBI_MARKETPLACE_ROOT/scripts/record-learning.sh"` writes the note, runs the hygiene scan,
commits to a branch and opens a pull request.

If it is unset, the skills are loading from a read-only plugin cache and an edit there is discarded
by the next `plugin update`. Write the note to the agent's memory file instead, and say plainly in
the note that it still needs promoting into the plugin.

Nothing portable belongs in `~/.claude/rules/`, `.cursor/rules/` or `.github/instructions/`. Those
are per-machine and per-user.
<!-- boundary-rule:end -->

## Applying it

- **One fact, one place.** Correct a stale entry, move a still-true entry that is in the wrong file,
  and never delete a verified fact to make room. There is no length cap on a reference file, because
  progressive disclosure means it is only loaded when the agent opens it.
- **Improve the copy that exists** rather than restating it somewhere else. A second copy is a
  future contradiction.
- **Not a change log.** Write the active reference note ("`QueryGroup` returns an object; access
  `.Folder` for the name string"), not the history of how it was found.
- **Cross-reference by `plugin:skill` name plus reference filename**, never by filesystem path.
  That form survives a repo move, a Codespace checkout at a different path, and the Codex projection
  into `~/.agents/skills/`.

## Checks

```bash
python scripts/check-skill-hygiene.py          # dated claims, leakage, denylist, dead links
python scripts/check-skill-hygiene.py --staged # the same, over staged files only
bash scripts/validate-plugins.sh               # plugin and marketplace manifests
```

`scripts/denylist-add.py` adds a term to the personal-data denylist by hash, so the tracked
denylist never contains the terms it protects.
