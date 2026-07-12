"""Extract / embed the Vega(-Lite) spec inside a Deneb PBIR visual.json.

Deneb stores its spec at visual.objects.vega[0].properties.jsonSpec.expr.Literal.Value
as a PBIR string literal: single-quote wrapped, embedded single quotes doubled ('').
Editing that by hand (or with ad-hoc inline scripts) is error-prone — use this instead.

Usage:
  python deneb_spec.py extract <visual.json> [-o spec.json] [--config config.json]
  python deneb_spec.py embed   <visual.json> --spec spec.json [--config config.json]

extract: writes the pretty-printed spec (and optionally jsonConfig) to files.
embed:   validates inputs parse as JSON first, re-escapes, writes visual.json back.
         A .bak copy of visual.json is saved next to it before any mutation.
"""
import argparse, json, os, shutil, sys

SPEC_PATH = ("visual", "objects", "vega", 0, "properties")

def get_props(doc):
    node = doc
    try:
        for k in SPEC_PATH:
            node = node[k]
    except (KeyError, IndexError, TypeError):
        sys.exit("ERROR: not a Deneb visual.json (no visual.objects.vega[0].properties)")
    return node

def literal_to_text(node, name):
    try:
        raw = node[name]["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return None
    if not (raw.startswith("'") and raw.endswith("'")):
        sys.exit(f"ERROR: {name} literal is not single-quote wrapped: {raw[:60]}")
    return raw[1:-1].replace("''", "'")

def set_literal(props, name, text):
    props[name] = {"expr": {"Literal": {"Value": "'" + text.replace("'", "''") + "'"}}}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["extract", "embed"])
    ap.add_argument("visual", help="Path to the Deneb visual.json")
    ap.add_argument("-o", "--out", help="extract: where to write the spec (default: spec.json next to the visual)")
    ap.add_argument("--spec", help="embed: spec file to embed")
    ap.add_argument("--config", help="extract: also write jsonConfig here / embed: also embed jsonConfig from here")
    args = ap.parse_args()

    with open(args.visual, encoding="utf-8") as f:
        doc = json.load(f)
    props = get_props(doc)

    if args.action == "extract":
        spec_text = literal_to_text(props, "jsonSpec")
        if spec_text is None:
            sys.exit("ERROR: no jsonSpec literal found")
        spec = json.loads(spec_text)  # validates
        out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.visual)), "spec.json")
        if os.path.normcase(os.path.abspath(out)) == os.path.normcase(os.path.abspath(args.visual)):
            sys.exit("ERROR: output path equals the visual.json input — refusing to overwrite it")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        provider = literal_to_text(props, "provider") or props.get("provider")
        print(f"spec -> {out}  (provider: {provider}, $schema: {spec.get('$schema', '?')})")
        if args.config:
            cfg_text = literal_to_text(props, "jsonConfig")
            if cfg_text:
                with open(args.config, "w", encoding="utf-8") as f:
                    json.dump(json.loads(cfg_text), f, indent=2, ensure_ascii=False)
                print(f"config -> {args.config}")
            else:
                print("note: visual has no jsonConfig literal; nothing written for --config")
    else:
        if not args.spec:
            sys.exit("ERROR: embed requires --spec")
        # validate ALL inputs before touching visual.json
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
        cfg = None
        if args.config:
            with open(args.config, encoding="utf-8") as f:
                cfg = json.load(f)
        shutil.copyfile(args.visual, args.visual + ".bak")
        set_literal(props, "jsonSpec", json.dumps(spec, indent=2, ensure_ascii=False))
        if cfg is not None:
            set_literal(props, "jsonConfig", json.dumps(cfg, separators=(",", ":"), ensure_ascii=False))
        with open(args.visual, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"embedded {args.spec} -> {args.visual} (backup: {args.visual}.bak)")

if __name__ == "__main__":
    main()
