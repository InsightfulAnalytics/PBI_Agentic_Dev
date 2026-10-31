# Finding titles

A title that states a finding computed from the card's own rows ("Billing & refunds is resolved
at first contact least often, 77.1%") is the strongest title a card can carry and the easiest to
make false. A 47-agent review of a nine-page app found most of its defects in these sentences,
not in the charts (1 Nov 2026). The same rules hold for a page's lede and for a Power BI title
measure.

Write each finding as a function of the rows the card draws, and read it with every filter the
page offers set, one at a time: most of the false sentences appeared only under a filter.

## The rules

1. **Floor every comparison.** A sentence that names the best or worst member needs enough rows
   behind each side: titles had named issues on 1 to 8 tickets and members on one survey answer.
   Judge only members over a floor (30 tickets, or 30 answers, did here). When nothing clears it,
   say that instead of a finding.
2. **A filter can leave one member.** A driver that a page filter narrows to one member has no
   spread: a channel filter made "channel moves CSAT least, 0.00 points". Skip a driver with
   fewer than two members.
3. **Compare the figures as shown.** Take gaps, ranks, "higher" and "flat" from the rounded figures
   the sentence prints, not the raw values: "+0.00" carried an up arrow, and a spread of 0.08 sat
   between 4.00 and 4.09. Parse the formatted text back to a number, and read a change that
   rounds to zero as flat and unsigned.
4. **A signed gap is not a size.** "Within 5 points" must test the absolute gap, and "trails" must
   test the sign: one title counted an issue AI led by 6.5 points as within 5, and said AI trails
   on an issue it led.
5. **Weight averages by their denominators.** A mean of monthly ratios is not the period's ratio:
   "€13.32 on average" was €13.33 pooled. Divide the summed numerators by the summed denominators.
6. **Ties name every member or none.** A shown figure two members share is never credited to the
   one that sorted first.
7. **Test every "because".** A clause that explains (a mix shift, a driver) is a second finding:
   compute it. A month's cost peak was put down to its issue mix, which explained about a quarter
   of it; its technical tickets also cost 37% more. The title names both.
8. **The evidence is about the subject.** An action that names one escalation reason cited every
   reason's figures. Cite the named member's own comparison.
9. **The words follow the measure's definition.** Read the measure before naming it in a sentence:
   a rate of tickets solved at first closure, repeat contacts or not, is "marked resolved", not
   "resolved in the end".
10. **A selection changes the sentence.** When a chart click or filter selects the member a
    sentence compares, write a sentence about that member rather than a comparison it now spans.

## Reviewing them

Split the review by page, and give each reviewer the rules above, the page's queries and the
live app with filters to set. Reviewers that run while fixes land read the new working tree and
report findings as "refuted: already fixed": read each verdict's reason, not the verdict.
