# Where a new learning goes

Kept out of [SKILL.md](../SKILL.md) to keep the body under the compaction budget. The block between the
markers is a copy of the one in the repo's `LEARNINGS.md`: edit it there, then run
`python scripts/sync-boundary-rule.py`.

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
