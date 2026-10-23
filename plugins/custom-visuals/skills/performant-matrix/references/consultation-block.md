# Step 5: the consultation block

Moved out of [SKILL.md](../SKILL.md) so the skill body stays under the compaction budget.

Fill in the measured numbers and present it as written. Pre-check 1 (the measures are the floor) and
pre-check 2 (the bridge gate fails, so drop option 1) are in [Step 5](../SKILL.md#step-5-consult-the-user).

> Here is what your matrix is paying for, from the pinned-context measurements:
>
> - **Row dispatch**: `<dispatch query>` minus `<flat query>` = **`<X>` ms**
> - **Per-cell tax** (format strings + CF colour measures, invisible to `EVALUATE`): Performance Analyzer `<PA>` ms against a `<dispatch>` ms query leaves roughly **`<Y>` ms** unaccounted for
> - **Measure floor**: `<flat query>` ms. Nothing below this is reachable.
>
> Three ways forward. They are not equivalent, and the fastest one is not the one I would recommend by default.
>
> **1. Bridge the model, keep the native visual.**
> Add a physical line-to-account bridge table and a bidirectional relationship; the row measures stop asking "which row am I on" and start asking "which accounts does this row cover". Removes row dispatch at the source.
> *Buys:* on the lab's account-shaped P&L, 4,815 ms to 348 ms cold (13.8x) and 4,594 ms to 319 ms warm.
> *Costs:* a model change, and a bidirectional relationship on a shared dimension can create ambiguous filter paths. I check the blast radius before committing, and RLS needs `securityFilteringBehavior` set separately.
> *Keeps:* native sorting, drill, export to Excel, the conditional-formatting UI, and every future visual inherits it.
>
> **2. Restructure natively, no new tables.**
> Static format strings where the column shares an order of magnitude; kill any `formatStringDefinition` that references its own measure; collapse CF colour measures to a colour column or a static rule; fewer measures on screen.
> *Buys:* the per-cell tax only. Measured: 182 cells went from 622 ms static to 1,270 ms with a self-referencing dynamic format string, so that half is real money.
> *Costs:* row dispatch stays. And a warning: replacing a `SWITCH` with a calculation group on rows made the same 182 cells **4.5x slower** (1,680 ms to 7,530 ms), so "modernising" the dispatch is not a fix.
> *Keeps:* everything. Zero model risk.
>
> **3. Rebuild the grid in Deneb.**
> One flat query, all cells derived client-side. Removes dispatch *and* the per-cell tax at once.
> *Buys:* on rows that are **not** an account set, 12,412 ms to 332 ms (37.4x cold, 69.5x warm), and 419 ms where every native alternative sat between 1,680 ms and 7,530 ms.
> *Costs:* you rebuild the grid chrome by hand. Column widths, headers, indentation, totals and colours are all spec. No native sort, no export, no drill, no CF pane. A Vega spec to maintain.
> *Note:* where the rows **are** an account set, Deneb only beats the bridge 294 ms to 348 ms. **The bridge wins on effort, not on time.**
>
> Which do you want? If you are unsure: **1** if your rows are an account set and you can change the model; **3** if they are not, or you specifically want client-side formatting and colour; **2** if the model is frozen.
