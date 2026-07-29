# Portable `pbir` binaries

A last resort, not an alternative. Install `pbir` with `uv tool install pbir-cli` or
`pip install pbir-cli` in every ordinary case, including when the command is missing.

Use this folder **only** when `pbir` is not installed *and* cannot be: no network access to
PyPI, no Python, or a machine that forbids installs. A portable build does not update with
`uv tool upgrade`, so choosing it when a normal install would have worked strands you on a
stale CLI. If `pbir --version` already works, ignore this folder entirely.

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

Linux has no portable build. Install it with `uv tool install pbir-cli` or
`pip install pbir-cli`, which is the recommended route on macOS and Windows too.

## Running them

macOS: `tar -xzf pbir-portable-macos-arm64.tar.gz`, then run the extracted `pbir`. The
archive is notarized, so Gatekeeper will not block it.

Windows: run `pbir-portable-windows-x64.exe` directly. It is Authenticode signed.

## Deleting them

**Anything `fetch.sh` downloads here can be deleted whenever space is tight.** These are a
convenience copy, not a dependency: no instruction in `SKILL.md` reads from this folder, and
removing them leaves the skill fully working for anyone who installed `pbir` through pip or
uv. Re-run `fetch.sh` if you want them back.
