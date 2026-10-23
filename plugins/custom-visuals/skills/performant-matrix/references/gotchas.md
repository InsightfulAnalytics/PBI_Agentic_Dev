# Performant matrix: gotchas (hard-won)

Moved out of [SKILL.md](../SKILL.md) so the skill body stays under the compaction budget.

- **Removing `SWITCH` made it slower.** Replacing a 13-branch `SWITCH` with a second calculation group on rows took the same 182 cells from 1,680 ms to 7,530 ms, 4.5x *worse*. Cost is instantiation count, not branch count. "Calculation groups are the modern replacement for `SWITCH`" is not true for performance on this shape.
- **`IFERROR` on every branch more than doubled the cost:** 2,757 ms to 5,997 ms cold in the lab. If a branch can error, fix the branch.
- **Only calendar-registered columns are safe to group in a flat rebuild.** `DATEADD` shifts filters only on registered columns; an unregistered helper column of the same table sitting in the `GROUP BY` survives the shift, and every `*LY` measure returns `BLANK`. Symptom: current-period values perfect, prior-period all blank, no error anywhere. The fix costs no DAX: bind the column as an `Aggregation` field with `Function: 3` (Min). **Scope limit:** a classic marked date table (`dataCategory: Time`) does not have this problem, because `DATEADD` removes filters from every column of that table. The trap belongs to the modern `calendar` object, where registration is explicit and partial.
- **`null` coerces to `0` in JavaScript.** Guard derived thresholds in a Deneb spec with `isValid` and let them stay `null`, so dependent columns fail closed to blank. A visibly empty column gets reported; a plausible one ships.
- **The format-string A/B, the number to quote:** 182 cells warm, 622 ms with a static format string, 1,270 ms with a dynamic one that references its own measure. Same measure, same query, same cells.
- **With two calculation groups the higher-precedence group's format string wins outright**, and `SELECTEDMEASUREFORMATSTRING()` inside it returns the *base measure's* format string. The lower group's format strings are never consulted at all.
- **A clean `pbir validate` and a clean DAX profile are not evidence the visual is fast.** Neither one looks at formatting. The canvas is the referee.
