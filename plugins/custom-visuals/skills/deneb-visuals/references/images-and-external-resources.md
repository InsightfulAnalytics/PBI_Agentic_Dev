# Images and external resources

Moved out of [SKILL.md](../SKILL.md) so the skill body stays under the compaction budget.

Deneb **cannot fetch anything**. Not an image, not a dataset, not a font. This is not a setting.

The gate is a build time Webpack flag, `ALLOW_EXTERNAL_URI`, inlined by DefinePlugin and `false` in
the certified, alpha and beta builds. Only the uncertified **standalone** build
(`deneb.standalone.*.pbiviz`, GUID prefixed `STANDALONE`) patches in `WebAccess` with
`parameters: ['*']`, and it trades away export to PDF and PowerPoint, subscription rendering, and
possibly Publish to web. For a report anyone else will open, treat remote resources as unavailable.

A blocked resource fails **quietly**: the loader resolves it to a blank base64 PNG and shows a
warning icon in the visual header. Nothing throws, so a spec that looks correct simply renders empty
images.

`data:` URIs do work, but the loader's regex is fussy about the prefix:

| Prefix | Result |
|---|---|
| `data:image/svg+xml;charset=utf-8,` | accepted |
| `data:image/svg+xml;base64,` | accepted |
| `data:image/svg+xml,` (bare comma) | accepted |
| `data:image/svg+xml;utf8,` | **rejected** |
| `data:image/svg+xml;utf-8,` | **rejected** |

That last pair is the trap, because `;utf8,` is the form used by every example in the
`svg-visuals` skill and by most DAX SVG material on the web. It is correct for a native table or
matrix `ImageUrl` cell and silently wrong here. If one measure feeds both, emit `;charset=utf-8,`.

Established by extracting the regex from Deneb's `loader.ts` and testing eleven URI forms against it.
**Not yet reproduced inside Deneb in product**, so confirm before relying on it.

Storing an image in the model instead has its own ceiling: Power Query silently truncates any text
cell over 32,766 characters, capping a base64 payload at roughly 24 KB of source image.
