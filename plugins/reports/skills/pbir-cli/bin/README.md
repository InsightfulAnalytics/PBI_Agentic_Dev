# Portable `pbir` binaries

A last resort, not an alternative. Install `pbir` with `uv tool install pbir-cli` or
`pip install pbir-cli` in every ordinary case on macOS and Windows, including when the
command is missing. On Linux neither command works: see the Linux note below.

Use this folder **only** on macOS or Windows, when `pbir` is not installed *and* cannot be:
no network access to PyPI, no Python, or a machine that forbids installs. A portable build
does not update with `uv tool upgrade`, so choosing it when a normal install would have
worked strands you on a stale CLI. If `pbir --version` already works, ignore this folder
entirely.

The binaries are not committed. The Windows build alone is ~180 MB, past GitHub's 100 MB
per-file limit, and nobody installing an unrelated plugin from this marketplace should pay
for a quarter-gigabyte clone. Fetch them on demand instead:

```bash
./fetch.sh            # newest release
./fetch.sh v0.9.29    # a specific one
```

That downloads the build matching your platform into this folder:

```
pbir-portable-macos-arm64.tar.gz    macOS, Apple silicon      ~66 MB
pbir-portable-windows-x64.exe       Windows x64              ~180 MB
```

Linux has no portable build and no installable one either. Every `pbir-cli` release
publishes exactly two wheels, `macosx_11_0_arm64` and `win_amd64`, and no sdist, so both
`pip install pbir-cli` and `uv tool install pbir-cli` fail there with "No matching
distribution found for pbir-cli". That is absence, not a degraded mode: do not spend turns
retrying the install. On Linux, hand-author PBIR JSON from the `pbip:pbir-format` skill's
`examples/visuals/` templates, check every file's JSON syntax with `jq empty` and its
structure against that skill's `references/validation.md`, then with the user's permission
publish the report to a sandbox workspace with `fab import` (byConnection reports only;
always pass `-f`), and verify by rendering the report server-side through the Power BI
ExportTo API. Installing is the recommended route on macOS and Windows.

## Running them

macOS: `tar -xzf pbir-portable-macos-arm64.tar.gz`, then run the extracted `pbir`. The
archive is notarized, so Gatekeeper will not block it.

Windows: run `pbir-portable-windows-x64.exe` directly. It is Authenticode signed.

## Deleting them

**Anything `fetch.sh` downloads here can be deleted whenever space is tight.** These are a
convenience copy, not a dependency: no instruction in `SKILL.md` reads from this folder, and
removing them leaves the skill fully working for anyone who installed `pbir` through pip or
uv. Re-run `fetch.sh` if you want them back.
