# Attributions

Original project and author: [Kurt Buhler](https://github.com/data-goblin) · [Data Goblins](https://data-goblins.com) — this repo is a fork of [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development); see [FORK-CHANGES.md](FORK-CHANGES.md) for what the fork changed.

## Third-party code bundled in this fork

The `semantic-models/date-table` skill redistributes two pieces of community code. Neither carries an explicit licence; both were published freely by their authors. Attribution headers are kept inline in the bundled TMDL — retain them if you copy the assets elsewhere.

- **Extended Date Table (`fnDateTable` Power Query M function):** original author [Melissa de Korte](https://gist.github.com/m-dekorte), published on the [Enterprise DNA forum](https://forum.enterprisedna.co/t/extended-date-table-power-query-m-function/6390) ([gist](https://gist.github.com/m-dekorte/12b53faee9cc1a616fa23f15b1b4a173)). This copy was taken from [Brian Julius's mirror](https://gist.github.com/bjulius/24533d0a6eb4110fcebbb3c19e70ae44) and locally modified — renamed and added output columns, removed the raw ISO columns (see the skill's `references/column-reference.md`).
- **`Dates Selected` DAX measure:** [Rick de Groot](https://datahub.nl) / Datahub, ["Showing period selections in Power BI"](https://datahub.nl/showing-period-selections-in-power-bi/).

## Community contributions to the upstream project

Community contributions and suggestions that shaped the upstream project:

- **Fabric CLI skill; Using DuckDB to query Lakehouse Tables:** Approach suggested by [Jan Hoet](https://www.linkedin.com/feed/update/urn:li:ugcPost:7443280165612249088?commentUrn=urn%3Ali%3Acomment%3A%28ugcPost%3A7443280165612249088%2C7443321316507680768%29&replyUrn=urn%3Ali%3Acomment%3A%28ugcPost%3A7443280165612249088%2C7445408056752041985%29&dashCommentUrn=urn%3Ali%3Afsd_comment%3A%287443321316507680768%2Curn%3Ali%3AugcPost%3A7443280165612249088%29&dashReplyUrn=urn%3Ali%3Afsd_comment%3A%287445408056752041985%2Curn%3Ali%3AugcPost%3A7443280165612249088%29).
- **Fabric CLI skill; Notebook-less Livy API execution:** Approach suggested by [Alex Dupler](https://x.com/alexdupler).
- **DAX optimization skill:** Contributed by [Justin Martin](https://daxnoob.blog).
- **Power BI Desktop APIs and agentic development:** Microsoft is exposing new APIs in Power BI Desktop and investing in Power BI agentic development to make it easier:
  - [@microsoft/powerbi-desktop-bridge-cli](https://www.npmjs.com/package/@microsoft/powerbi-desktop-bridge-cli)
  - [@microsoft/powerbi-report-authoring-cli](https://www.npmjs.com/package/@microsoft/powerbi-report-authoring-cli)
  - [@microsoft/powerbi-core-visual-schema](https://www.npmjs.com/package/@microsoft/powerbi-core-visual-schema)
  - [@microsoft/powerbi-modeling-mcp](https://www.npmjs.com/package/@microsoft/powerbi-modeling-mcp)
