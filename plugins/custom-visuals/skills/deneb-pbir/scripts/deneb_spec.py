"""Extract / embed / audit / migrate the Vega(-Lite) spec inside a Deneb PBIR visual.json.

Deneb stores its spec at visual.objects.vega[0].properties.jsonSpec.expr.Literal.Value
as a PBIR string literal: single-quote wrapped, embedded single quotes doubled ('').
Editing that by hand (or with ad-hoc inline scripts) is error-prone, so use this instead.

Usage:
  python deneb_spec.py extract <visual.json> [-o spec.json] [--config config.json]
  python deneb_spec.py embed   <visual.json> --spec spec.json [--config config.json] [--keep-schema]
  python deneb_spec.py audit   <visual.json | spec.json> [--json]
  python deneb_spec.py migrate <visual.json | spec.json> [--signals modern|legacy] [--strip-schema] [--dry-run]

extract: writes the pretty-printed spec (and optionally jsonConfig) to files. A spec with
         no root $schema gets the v6 URL for the visual's provider so editors and the
         offline renderer can use it.
embed:   validates inputs parse as JSON first, strips a root $schema (Deneb warns on one in
         the Specification editor; pass --keep-schema to keep it), re-escapes, writes
         visual.json back. A .bak copy is saved next to it before any mutation.
audit:   reports the Deneb build stamp, provider and version, denebMetaVersion, 2.0-only
         properties, legacy pbiContainer* and denebContainer references, root $schema,
         __identity__ / __key__ leftovers, the enableContextMenu false semantics trap,
         supportFieldConfiguration parse state, field parameters, template usermeta
         version, and a one-line verdict. Exits 0 whenever the file parses (it reports);
         a file that is not JSON or JSONC, or a jsonSpec literal that is not single-quote
         wrapped, exits 1 with an ERROR: line and no verdict.
migrate: rewrites container signal names (--signals modern: pbiContainer* to
         denebContainer.*, --signals legacy: the reverse) and/or removes a root $schema
         (--strip-schema), on a PBIR visual.json (inside the jsonSpec literal) or on a bare
         spec/template JSON file. Writes a .bak first; refuses when nothing would change;
         --dry-run prints the counts and writes nothing.

audit and migrate accept either a PBIR visual.json (detected by visual.objects.vega) or a
bare spec / template file. Signal detection uses the same word-boundary patterns as Deneb
2.0 (packages/vega-runtime/src/lib/signals/migration.ts), so a legacy name inside a plain
string literal is counted and rewritten too.

Deneb accepts JSONC (// and /* */ comments) in the spec and config editors and strips the
comments before JSON.parse (packages/utils/src/lib/jsonc.ts). Every command here does the
same when strict JSON parsing fails; extract and embed then write plain JSON, so comments
do not survive a round trip. migrate rewrites text in place and keeps them.
"""
import argparse, json, os, re, shutil, sys

SPEC_PATH = ("visual", "objects", "vega", 0, "properties")
SCHEMA_URLS = {
    "vega": "https://vega.github.io/schema/vega/v6.json",
    "vegaLite": "https://vega.github.io/schema/vega-lite/v6.json",
}
# Deneb 2.0 rewrite order (migration.ts): the specific names first, then the bare object.
LEGACY_TO_MODERN = [
    ("pbiContainerWidth", "denebContainer.width"),
    ("pbiContainerHeight", "denebContainer.height"),
    ("pbiContainer", "denebContainer"),
]
MODERN_TO_LEGACY = [
    ("denebContainer.width", "pbiContainerWidth"),
    ("denebContainer.height", "pbiContainerHeight"),
    ("denebContainer", "pbiContainer"),
]
MODERN = "denebContainer"
# Properties that only exist in Deneb 2.0 capabilities (1.9.1 to 2.0 delta).
NEW_IN_2_0 = [
    ("vega", "enableContextMenuSelector"),
    ("display", "scrollbarWidth"),
    ("dataLimit", "enableIncrementalDataUpdates"),
    ("dataLimit", "incrementalUpdateThreshold"),
    ("stateManagement", "supportFieldConfiguration"),
    ("stateManagement", "denebMetaVersion"),
    ("stateManagement", "scaleToZoom"),
    ("stateManagement", "consolidateFieldParameters"),
]
REMOVED_FIELDS = ["__identity__", "__key__"]
V2_KEY_RE = re.compile(r"^__[a-zA-Z0-9_]+\.\d+__$")
# Supporting-field suffixes (packages/data-core/src/lib/field/constants.ts) and the flag that
# switches each one on in supportFieldConfiguration.
SUPPORT_SUFFIXES = ("highlight", "highlightStatus", "highlightComparator", "format", "formatted", "names")
HIGHLIGHT_REF_RE = re.compile(r"__highlight(?:Status|Comparator)?\b")


def wb(name):
    return re.compile(r"\b" + re.escape(name) + r"\b")


def count_refs(text, name):
    return len(wb(name).findall(text))


def count_legacy(text):
    return sum(count_refs(text, name) for name, _ in LEGACY_TO_MODERN)


def rewrite(text, pairs):
    for src, dst in pairs:
        text = wb(src).sub(dst, text)
    return text


# ---------------------------------------------------------------- JSONC

def strip_jsonc_comments(text):
    """Blank out // and /* */ comments outside strings, keeping every offset and line break.

    Mirrors Deneb's stripComments (packages/utils/src/lib/jsonc.ts): comments become spaces,
    nothing else changes, so error positions still point at the author's text.
    """
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
        elif ch == '"':
            in_str = True
            out.append(ch)
            i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif ch == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(c if c in "\r\n" else " " for c in text[i:j]))
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def loads_lenient(text):
    """json.loads that falls back to stripping JSONC comments. Returns (obj, had_comments)."""
    try:
        return json.loads(text), False
    except ValueError:
        stripped = strip_jsonc_comments(text)
        if stripped == text:
            raise
        return json.loads(stripped), True


def load_json_lenient(path):
    with open(path, encoding="utf-8") as f:
        return loads_lenient(f.read())


# ---------------------------------------------------------------- PBIR literal helpers

def get_props(doc):
    node = doc
    try:
        for k in SPEC_PATH:
            node = node[k]
    except (KeyError, IndexError, TypeError):
        sys.exit("ERROR: not a Deneb visual.json (no visual.objects.vega[0].properties)")
    return node


def is_pbir_visual(doc):
    node = doc
    try:
        for k in SPEC_PATH:
            node = node[k]
        return isinstance(node, dict)
    except (KeyError, IndexError, TypeError):
        return False


def literal_to_text(node, name):
    try:
        raw = node[name]["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return None
    if not isinstance(raw, str):
        return None
    if not (raw.startswith("'") and raw.endswith("'")):
        sys.exit(f"ERROR: {name} literal is not single-quote wrapped: {raw[:60]}")
    return raw[1:-1].replace("''", "'")


def set_literal(props, name, text):
    props[name] = {"expr": {"Literal": {"Value": "'" + text.replace("'", "''") + "'"}}}


def object_literal(doc, obj, name):
    """Raw Literal.Value of visual.objects.<obj>[0].properties.<name>, or None."""
    try:
        node = doc["visual"]["objects"][obj][0]["properties"][name]
        return node["expr"]["Literal"]["Value"]
    except (KeyError, IndexError, TypeError):
        return None


def unquote(raw):
    """PBIR text literal ('abc') to abc; booleans/numbers ('true', '50D') returned as-is."""
    if raw is None:
        return None
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    return raw


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_doc(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------- root $schema (text level)

def strip_root_schema_text(text):
    """Remove the root-level "$schema" member from JSON text, keeping the rest byte for byte.

    Returns (new_text, removed). When the member cannot be cut out textually the document
    is re-serialised (indent 2) without it instead.
    """
    try:
        doc, _ = loads_lenient(text)
    except ValueError:
        return text, False
    if not isinstance(doc, dict) or "$schema" not in doc:
        return text, False
    expected = dict(doc)
    del expected["$schema"]
    for m in re.finditer(r'"\$schema"\s*:\s*"(?:[^"\\]|\\.)*"', text):
        if _depth_at(text, m.start()) != 1:
            continue
        start, end = m.start(), m.end()
        tail = re.match(r"\s*,\s*", text[end:])
        if tail:
            end += tail.end()
        else:
            head = re.search(r",\s*$", text[:start])
            if head:
                start = head.start()
        candidate = text[:start] + text[end:]
        try:
            if loads_lenient(candidate)[0] == expected:
                return candidate, True
        except ValueError:
            pass
        break
    return json.dumps(expected, indent=2, ensure_ascii=False), True


def _depth_at(text, pos):
    depth = 0
    in_str = False
    esc = False
    for ch in text[:pos]:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
    return depth


# ---------------------------------------------------------------- extract / embed

def cmd_extract(args):
    doc = load_json(args.file)
    props = get_props(doc)
    spec_text = literal_to_text(props, "jsonSpec")
    if spec_text is None:
        sys.exit("ERROR: no jsonSpec literal found")
    spec, had_comments = loads_lenient(spec_text)  # validates; tolerates JSONC like Deneb
    provider = unquote(object_literal(doc, "vega", "provider")) or "vegaLite"
    added_schema = False
    if isinstance(spec, dict) and "$schema" not in spec:
        spec = {"$schema": SCHEMA_URLS.get(provider, SCHEMA_URLS["vegaLite"]), **spec}
        added_schema = True
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.file)), "spec.json")
    if os.path.normcase(os.path.abspath(out)) == os.path.normcase(os.path.abspath(args.file)):
        sys.exit("ERROR: output path equals the visual.json input; refusing to overwrite it")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    note = " (added for the provider; embed strips it again)" if added_schema else ""
    print(f"spec -> {out}  (provider: {provider}, $schema: {spec.get('$schema', '?')}{note})")
    if had_comments:
        print("note: jsonSpec carried JSONC comments; they were stripped, the extracted file is plain JSON")
    if args.config:
        cfg_text = literal_to_text(props, "jsonConfig")
        if cfg_text:
            with open(args.config, "w", encoding="utf-8") as f:
                json.dump(loads_lenient(cfg_text)[0], f, indent=2, ensure_ascii=False)
            print(f"config -> {args.config}")
        else:
            print("note: visual has no jsonConfig literal; nothing written for --config")


def cmd_embed(args):
    doc = load_json(args.file)
    props = get_props(doc)
    # validate ALL inputs before touching visual.json (JSONC comments are stripped, as Deneb does)
    try:
        spec, spec_comments = load_json_lenient(args.spec)
    except ValueError as exc:
        sys.exit(f"ERROR: {args.spec} is not JSON (nor JSONC): {exc}")
    try:
        cfg, cfg_comments = load_json_lenient(args.config) if args.config else (None, False)
    except ValueError as exc:
        sys.exit(f"ERROR: {args.config} is not JSON (nor JSONC): {exc}")
    if spec_comments or cfg_comments:
        print("note: JSONC comments in the input were stripped; the embedded text is plain JSON")
    stripped = False
    if isinstance(spec, dict) and "$schema" in spec and not args.keep_schema:
        del spec["$schema"]
        stripped = True
    shutil.copyfile(args.file, args.file + ".bak")
    set_literal(props, "jsonSpec", json.dumps(spec, indent=2, ensure_ascii=False))
    if cfg is not None:
        set_literal(props, "jsonConfig", json.dumps(cfg, separators=(",", ":"), ensure_ascii=False))
    write_doc(args.file, doc)
    note = "; root $schema stripped (use --keep-schema to keep it)" if stripped else ""
    print(f"embedded {args.spec} -> {args.file} (backup: {args.file}.bak{note})")


# ---------------------------------------------------------------- audit

def audit_spec_text(spec_text, report):
    """Findings that apply to the spec text whether it came from PBIR or a bare file."""
    report["legacySignalReferences"] = {
        name: count_refs(spec_text, name) for name, _ in LEGACY_TO_MODERN
    }
    report["legacySignalReferencesTotal"] = count_legacy(spec_text)
    report["denebContainerReferences"] = count_refs(spec_text, MODERN)
    report["removedFieldReferences"] = {f: count_refs(spec_text, f) for f in REMOVED_FIELDS}
    try:
        spec, had_comments = loads_lenient(spec_text)
    except ValueError as exc:
        report["specParses"] = False
        report["specParseError"] = str(exc)
        return None
    report["specParses"] = True
    report["specHasComments"] = had_comments
    report["rootSchema"] = spec.get("$schema") if isinstance(spec, dict) else None
    um = spec.get("usermeta") if isinstance(spec, dict) else None
    if isinstance(um, dict):
        report["usermeta"] = audit_usermeta(um)
    return spec


def audit_usermeta(um):
    info = {"present": True}
    deneb = um.get("deneb") if isinstance(um.get("deneb"), dict) else {}
    info["metaVersion"] = deneb.get("metaVersion")
    info["provider"] = deneb.get("provider")
    info["providerVersion"] = deneb.get("providerVersion")
    entries = []
    shape = None
    if isinstance(um.get("datasets"), dict):
        shape = "v2 (usermeta.datasets)"
        for ds in um["datasets"].values():
            if isinstance(ds, list):
                entries.extend(e for e in ds if isinstance(e, dict))
    if isinstance(um.get("dataset"), list):
        shape = "v1 (usermeta.dataset array)" if shape is None else shape + " + v1 dataset array"
        entries.extend(e for e in um["dataset"] if isinstance(e, dict))
    keys = [e.get("key") for e in entries if isinstance(e.get("key"), str)]
    bad_keys = [k for k in keys if not V2_KEY_RE.match(k)]
    info["datasetShape"] = shape
    info["placeholderKeys"] = keys
    info["nonV2Keys"] = bad_keys
    info["isV1"] = bool(
        deneb.get("metaVersion") == 1
        or (shape is not None and shape.startswith("v1"))
        or bad_keys
    )
    inter = um.get("interactivity")
    if isinstance(inter, dict):
        info["interactivity"] = inter
        info["contextMenuSelectorMissing"] = "contextMenuSelector" not in inter
    return info


def parse_support_field_configuration(raw_text):
    """raw_text is the unquoted literal. Returns (state, parsed_or_None, note)."""
    if raw_text is None:
        return "absent", None, ""
    if raw_text.strip() == "":
        return "empty", {}, ""
    try:
        parsed = json.loads(raw_text)
    except ValueError as exc:
        return "unparseable", None, f"Deneb degrades it to {{}} with a warning: {exc}"
    if not isinstance(parsed, dict):
        return "unparseable", None, "not a JSON object"
    base = ("highlight", "highlightStatus", "highlightComparator", "format", "formatted")
    problems = []
    for field, flags in parsed.items():
        if not isinstance(flags, dict):
            problems.append(f"{field}: not an object")
            continue
        missing = [b for b in base if b not in flags]
        if missing:
            problems.append(f"{field}: missing {', '.join(missing)} (read as false)")
        nonbool = [k for k, v in flags.items() if not isinstance(v, bool)]
        if nonbool:
            problems.append(f"{field}: non-boolean {', '.join(nonbool)}")
    return ("ok" if not problems else "partial"), parsed, "; ".join(problems)


def support_field_mismatches(spec_text, parsed):
    """Supporting fields the spec reads whose flag is off or missing in supportFieldConfiguration.

    Keys are the encoded display names, which are also the column names Vega sees, so
    `<key>__<suffix>` in the spec text is the reference to look for. A missing flag reads
    as false on the PBIR load path (build-processing-plan.ts 149-153).
    """
    found = []
    for field, flags in (parsed or {}).items():
        if not isinstance(flags, dict):
            continue
        for suffix in SUPPORT_SUFFIXES:
            name = f"{field}__{suffix}"
            if re.search(re.escape(name) + r"\b", spec_text) and flags.get(suffix) is not True:
                found.append(name)
    return found


def field_parameter_summary(fp):
    col = ((fp.get("parameterExpr") or {}).get("Column") or {})
    return {
        "entity": ((col.get("Expression") or {}).get("SourceRef") or {}).get("Entity"),
        "property": col.get("Property"),
        "index": fp.get("index"),
        "length": fp.get("length"),
    }


def cmd_audit(args):
    with open(args.file, encoding="utf-8") as f:
        raw = f.read()
    try:
        doc, _ = loads_lenient(raw)
    except ValueError as exc:
        sys.exit(f"ERROR: {args.file} is not JSON (nor JSONC): {exc}")
    report = {"file": args.file}
    verdict = []

    if is_pbir_visual(doc):
        report["kind"] = "pbir-visual"
        props = get_props(doc)
        dev_version = unquote(object_literal(doc, "developer", "version"))
        vega_version = unquote(object_literal(doc, "vega", "version"))
        provider = unquote(object_literal(doc, "vega", "provider"))
        report["developerVersion"] = dev_version
        report["provider"] = provider or "vegaLite (default, property absent)"
        report["providerVersion"] = vega_version
        # Versioned means BOTH stamps are present (migration.ts isVersionedSpec).
        report["versioned"] = bool(dev_version) and bool(vega_version)
        meta = unquote(object_literal(doc, "stateManagement", "denebMetaVersion"))
        report["denebMetaVersion"] = meta
        present = [f"{o}.{p}" for o, p in NEW_IN_2_0 if object_literal(doc, o, p) is not None]
        report["propertiesNewIn2_0"] = present
        cm = unquote(object_literal(doc, "vega", "enableContextMenu"))
        cms = unquote(object_literal(doc, "vega", "enableContextMenuSelector"))
        eh = unquote(object_literal(doc, "vega", "enableHighlight"))
        report["enableContextMenu"] = cm
        report["enableContextMenuSelector"] = cms
        report["enableHighlight"] = eh
        sfc_raw = unquote(object_literal(doc, "stateManagement", "supportFieldConfiguration"))
        state, parsed, note = parse_support_field_configuration(sfc_raw)
        report["supportFieldConfiguration"] = {
            "state": state,
            "fields": sorted(parsed) if parsed else [],
            "note": note,
        }
        cfp = unquote(object_literal(doc, "stateManagement", "consolidateFieldParameters"))
        report["consolidateFieldParameters"] = cfp
        try:
            fps = doc["visual"]["query"]["queryState"]["dataset"].get("fieldParameters") or []
        except (KeyError, TypeError, AttributeError):
            fps = []
        report["fieldParameters"] = [field_parameter_summary(fp) for fp in fps if isinstance(fp, dict)]
        spec_text = literal_to_text(props, "jsonSpec")
        highlight_refs = 0
        mismatches = []
        if spec_text is None:
            report["specParses"] = False
            report["specParseError"] = "no jsonSpec literal"
            verdict.append("no jsonSpec literal")
        else:
            audit_spec_text(spec_text, report)
            highlight_refs = len(HIGHLIGHT_REF_RE.findall(spec_text))
            mismatches = support_field_mismatches(spec_text, parsed)
        report["highlightReferences"] = highlight_refs
        report["supportFieldMismatches"] = mismatches

        # Verdict lines (PBIR-specific)
        if not dev_version:
            verdict.append("unstamped (no developer.version): Deneb 2.0 stamps it on first edit-mode open and treats a real spec as a migrated 1.x project")
        elif not report["versioned"]:
            verdict.append("half-stamped (developer.version without vega.version, or the reverse): Deneb treats it as unversioned, no context-menu remap")
        elif dev_version.startswith("2."):
            verdict.append(f"saved by Deneb {dev_version}: use denebContainer.* in this spec")
        else:
            verdict.append(f"saved by Deneb {dev_version}: keep pbiContainerWidth / pbiContainerHeight until the report is confirmed on 2.0")
        has_meta = meta not in (None, "")
        has_sfc = state not in ("absent", "empty")
        if (has_meta or has_sfc) and cfp is None:
            verdict.append("TRAP: denebMetaVersion or supportFieldConfiguration is present without consolidateFieldParameters; Deneb 2.0 then defaults consolidation ON (stamp all three together or none)")
        if has_sfc and not has_meta:
            verdict.append("supportFieldConfiguration without denebMetaVersion: unlisted fields get new-project defaults, not legacy ones")
        if state in ("unparseable", "partial"):
            verdict.append(f"supportFieldConfiguration {state}: {note}")
        if cm == "false":
            if cms is None:
                verdict.append("enableContextMenu false: under 2.0 an unstamped or 2.0-stamped visual HIDES the Power BI context menu; 1.9 read it as menu shown without data-point resolution. Author enableContextMenu true + enableContextMenuSelector false for the old meaning")
            else:
                verdict.append("enableContextMenu false: the Power BI context menu is hidden under 2.0 (right-click swallowed)")
        if highlight_refs and eh != "true":
            msg = f"spec reads __highlight* ({highlight_refs} reference(s)) but enableHighlight is not true: Deneb emits no __highlight fields"
            if not has_meta:
                msg += "; under 2.0 the first-open legacy stamp then freezes highlight false on every measure until the companion is ticked in the Supporting Fields: dataset section of the Project setup pane (read from source, not observed). Author enableHighlight true before the first 2.0 open, or stamp supportFieldConfiguration"
            verdict.append(msg)
        if mismatches:
            verdict.append("supporting field(s) read by the spec but off or missing in supportFieldConfiguration: "
                           + ", ".join(mismatches) + " (they arrive undefined under 2.0)")
        if report["fieldParameters"]:
            names = ", ".join(str(fp["property"]) for fp in report["fieldParameters"])
            # Deneb's code default for an absent consolidateFieldParameters is true
            # (src/lib/persistence/model/constants.ts line 57,
            # src/lib/state/project-sync-mappings.ts lines 225-228); only the legacy
            # migration of a fully unstamped file (no denebMetaVersion, empty
            # supportFieldConfiguration) pins it false.
            if cfp == "true":
                mode = "consolidated"
            elif cfp == "false":
                mode = "pass-through (consolidateFieldParameters false)"
            elif has_meta or has_sfc:
                mode = "consolidated (consolidateFieldParameters absent; the code default is true once denebMetaVersion or supportFieldConfiguration is present)"
            else:
                mode = "pass-through (unstamped: the legacy migration pins consolidateFieldParameters false)"
            verdict.append(f"field parameter(s) bound: {names}; 2.0 treats them as {mode}")
        if present:
            verdict.append(f"2.0-only properties present: {', '.join(present)} (1.9.1 tolerance unverified)")
    else:
        report["kind"] = "spec-or-template"
        audit_spec_text(raw, report)
        um = report.get("usermeta") or {}
        provider = um.get("provider")
        schema = report.get("rootSchema") or ""
        if not provider:
            provider = "vegaLite" if "vega-lite" in schema else ("vega" if "vega" in schema else None)
            provider = f"{provider} (inferred from $schema)" if provider else "unknown (no usermeta.deneb.provider, no $schema)"
        report["provider"] = provider
        report["providerVersion"] = um.get("providerVersion")
        if um:
            if um.get("isV1"):
                verdict.append("template usermeta v1: Deneb 2.0 migrates __N__ index keys on import but NOT custom keys (read from source, unverified in the UI); convert offline")
            else:
                verdict.append("template usermeta v2")
            if um.get("contextMenuSelectorMissing") and (um.get("interactivity") or {}).get("contextMenu") is False:
                verdict.append("interactivity.contextMenu false without contextMenuSelector: imports as menu on + selector off")

    # Shared verdict lines
    legacy = report.get("legacySignalReferencesTotal", 0)
    modern = report.get("denebContainerReferences", 0)
    if legacy and modern:
        verdict.append(f"MIXED signals: {legacy} legacy + {modern} denebContainer references; 2.0 rewrites the legacy ones, "
                       "and 1.9 is expected to fail on denebContainer (inferred from Vega's parser, not reproduced in a 1.9.1 Desktop)")
    elif legacy:
        verdict.append(f"{legacy} legacy pbiContainer* reference(s): works on 1.9 and 2.x (2.0 rewrites at parse time, removal target 3.0)")
    elif modern:
        verdict.append(f"{modern} denebContainer reference(s): 2.0 only; expected to fail parsing on 1.9.x "
                       "(inferred from Vega's parser, not reproduced in a 1.9.1 Desktop)")
    if report.get("rootSchema"):
        verdict.append("root $schema present: Deneb 2.0 flags it in the editor; embed strips it, or run migrate --strip-schema")
    removed = {k: v for k, v in report.get("removedFieldReferences", {}).items() if v}
    if removed:
        verdict.append("removed field(s) referenced: " + ", ".join(f"{k} x{v}" for k, v in removed.items()) + " (gone since 1.9; use __row__)")
    if report.get("specParses") is False:
        verdict.append(f"spec does not parse: {report.get('specParseError')}")
    if not verdict:
        verdict.append("no findings")
    report["verdict"] = verdict

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    print(f"file: {args.file}")
    print(f"kind: {report['kind']}")
    if report["kind"] == "pbir-visual":
        print(f"developer.version: {report['developerVersion'] or '(absent)'}")
        print(f"provider: {report['provider']}  vega.version: {report['providerVersion'] or '(absent)'}")
        print(f"versioned (both stamps): {report['versioned']}")
        print(f"denebMetaVersion: {report['denebMetaVersion'] or '(absent)'}")
        print(f"consolidateFieldParameters: {report['consolidateFieldParameters'] or '(absent)'}")
        print(f"2.0-only properties: {', '.join(report['propertiesNewIn2_0']) or '(none)'}")
        print(f"enableContextMenu: {report['enableContextMenu'] or '(absent, default true)'}  enableContextMenuSelector: {report['enableContextMenuSelector'] or '(absent, default true)'}")
        print(f"enableHighlight: {report['enableHighlight'] or '(absent, default false)'}  __highlight* references in spec: {report['highlightReferences']}")
        sfc = report["supportFieldConfiguration"]
        print(f"supportFieldConfiguration: {sfc['state']}"
              + (f" fields={sfc['fields']}" if sfc["fields"] else "")
              + (f" ({sfc['note']})" if sfc["note"] else "")
              + (f" mismatches={report['supportFieldMismatches']}" if report["supportFieldMismatches"] else ""))
        fps = report["fieldParameters"]
        print("fieldParameters: " + (", ".join(
            f"{fp['entity']}[{fp['property']}] index={fp['index']} length={fp['length']}" for fp in fps
        ) if fps else "(none)"))
    else:
        print(f"provider: {report['provider']}  providerVersion: {report.get('providerVersion') or '(absent)'}")
        um = report.get("usermeta")
        if um:
            print(f"usermeta: metaVersion={um.get('metaVersion')} shape={um.get('datasetShape')} keys={um.get('placeholderKeys')}"
                  + (f" nonV2Keys={um['nonV2Keys']}" if um.get("nonV2Keys") else ""))
        else:
            print("usermeta: (none, bare spec)")
    print(f"spec parses: {report.get('specParses')}" + (" (JSONC comments stripped)" if report.get("specHasComments") else ""))
    print(f"root $schema: {report.get('rootSchema') or '(none)'}")
    lr = report.get("legacySignalReferences", {})
    print(f"legacy signals: total={report.get('legacySignalReferencesTotal', 0)} " + " ".join(f"{k}={v}" for k, v in lr.items()))
    print(f"denebContainer references: {report.get('denebContainerReferences', 0)}")
    print("removed fields: " + " ".join(f"{k}={v}" for k, v in report.get("removedFieldReferences", {}).items()))
    print("verdict: " + " | ".join(verdict))


# ---------------------------------------------------------------- migrate

def migrate_text(spec_text, signals, strip_schema):
    """Return (new_text, changes dict)."""
    changes = {}
    new = spec_text
    if signals == "modern":
        n = count_legacy(new)
        if n:
            new = rewrite(new, LEGACY_TO_MODERN)
        changes["signalsRewritten"] = n
    elif signals == "legacy":
        n = count_refs(new, MODERN)
        if n:
            new = rewrite(new, MODERN_TO_LEGACY)
        changes["signalsRewritten"] = n
    if strip_schema:
        new, removed = strip_root_schema_text(new)
        changes["schemaStripped"] = removed
    return new, changes


def cmd_migrate(args):
    if not args.signals and not args.strip_schema:
        sys.exit("ERROR: migrate needs --signals modern|legacy and/or --strip-schema")
    with open(args.file, encoding="utf-8") as f:
        raw = f.read()
    try:
        doc, _ = loads_lenient(raw)
    except ValueError as exc:
        sys.exit(f"ERROR: {args.file} is not JSON (nor JSONC): {exc}")

    if is_pbir_visual(doc):
        props = get_props(doc)
        spec_text = literal_to_text(props, "jsonSpec")
        if spec_text is None:
            sys.exit("ERROR: no jsonSpec literal found")
        new_text, changes = migrate_text(spec_text, args.signals, args.strip_schema)
        changed = new_text != spec_text
        summary = f"{args.file} (pbir-visual): " + ", ".join(f"{k}={v}" for k, v in changes.items())
        if not changed:
            print(summary + "; nothing to change, file untouched")
            return
        if args.dry_run:
            print(summary + "; dry run, file untouched")
            return
        shutil.copyfile(args.file, args.file + ".bak")
        # Prefer a text-level replacement of the encoded literal so the rest of visual.json
        # stays byte for byte; fall back to re-serialising the document.
        old_lit = "'" + spec_text.replace("'", "''") + "'"
        new_lit = "'" + new_text.replace("'", "''") + "'"
        written = False
        for ascii_mode in (False, True):
            old_enc = json.dumps(old_lit, ensure_ascii=ascii_mode)
            if raw.count(old_enc) == 1:
                out = raw.replace(old_enc, json.dumps(new_lit, ensure_ascii=ascii_mode))
                json.loads(out)  # sanity
                with open(args.file, "w", encoding="utf-8") as f:
                    f.write(out)
                written = True
                break
        if not written:
            set_literal(props, "jsonSpec", new_text)
            write_doc(args.file, doc)
            summary += "; document re-serialised (indent 2)"
        print(summary + f"; written (backup: {args.file}.bak)")
    else:
        new_text, changes = migrate_text(raw, args.signals, args.strip_schema)
        changed = new_text != raw
        summary = f"{args.file} (spec-or-template): " + ", ".join(f"{k}={v}" for k, v in changes.items())
        if not changed:
            print(summary + "; nothing to change, file untouched")
            return
        if args.dry_run:
            print(summary + "; dry run, file untouched")
            return
        shutil.copyfile(args.file, args.file + ".bak")
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(new_text)
        print(summary + f"; written (backup: {args.file}.bak)")


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="action", required=True)

    p = sub.add_parser("extract", help="write the spec (and optionally jsonConfig) out of a visual.json")
    p.add_argument("file", metavar="visual.json")
    p.add_argument("-o", "--out", help="where to write the spec (default: spec.json next to the visual)")
    p.add_argument("--config", help="also write jsonConfig here")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("embed", help="write a spec (and optionally jsonConfig) back into a visual.json")
    p.add_argument("file", metavar="visual.json")
    p.add_argument("--spec", required=True, help="spec file to embed")
    p.add_argument("--config", help="also embed jsonConfig from here")
    p.add_argument("--keep-schema", action="store_true", help="keep a root $schema inside jsonSpec (default: strip it)")
    p.set_defaults(func=cmd_embed)

    p = sub.add_parser("audit", help="report Deneb version stamps, 2.0 properties and signal usage")
    p.add_argument("file", metavar="visual.json|spec.json")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("migrate", help="rewrite container signal names and/or strip a root $schema")
    p.add_argument("file", metavar="visual.json|spec.json")
    p.add_argument("--signals", choices=["modern", "legacy"], help="modern: pbiContainer* -> denebContainer.*; legacy: the reverse")
    p.add_argument("--strip-schema", action="store_true", help="remove a root $schema from the spec")
    p.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    p.set_defaults(func=cmd_migrate)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
