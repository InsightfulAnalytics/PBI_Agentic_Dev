---
name: audit-context
description: Review project context and agent configuration files (AGENTS.md, CLAUDE.md, memory files, skills, and others) to provide feedback and identify opportunities for improvement. Use when the user asks to audit, review, or improve their agent context, instructions, or memory files.
---

# Audit context

<!-- Ported from plugins/fabric-cli/commands/audit-context.md (Claude Code slash command) for Codex. -->

Audit the project's context configuration files, honoring any additional instructions the user gave.

Do not modify any files. Explore the project first if there are more than three markdowns to read.

## Agent configuration and memory files

Search for and read:

1. `AGENTS.md` files (root, nested directories) and `CLAUDE.md` files
2. Agent config: `.codex/config.toml`, `.claude/settings.json`, `.claude/settings.local.json`
3. Any `SKILL.md` files in the project
4. Memory or scratchpad files referenced by the above

For each file found, report:

1. Are memory and agent configuration files sufficiently short (ideally less than 500 lines) or too short (<50 lines)?
2. Are the context files relevant and up-to-date for the current project?
3. Do they mention when to automatically load the skills that are available, like `fabric-cli` or others?
4. Are they well-structured and concise, with headings, lists, examples, and commands?
5. Are they personalized for the project or generic?
6. Do they mention standard conventions like:
    - Recommending conciseness
    - Avoiding sycophancy or agreement and favoring critique and pushback within reason
    - Avoiding emojis in all responses
    - Formatting data with ASCII tables
    - When to ask for clarification
    - Where to get trustworthy information with web search and fetch
    - Avoiding excessive commenting in generated code
    - Following a strict separation of concerns with liberal composition of all code files produced
    - Documenting all tasks in a scratchpad directory and searching that directory before starting a new task
    - Creating any new files ONLY in the project tmp/ unless specified otherwise
    - Not creating test scripts or markdown summaries unless explicitly asked to
    - Never using TODOs, partial implementations, or stubs
    - Never saying "You're absolutely right!"
    - Never providing time estimates or talking about work in "Phases" or "Parts" unless explicitly asked to
    - When to use skills, custom commands, and MCP servers, if any are configured
    - How to avoid assumptions, particularly about how something works based on limited test cases
7. Are they absent, too little, or clearly AI-generated (risking "context rot")?
8. Do they follow "progressive disclosure" with reference of other relevant files, if they exist?

## Other project context

Search for other context like `spec.md` or `task.md`, or other markdown, txt, yaml, or similar files that provide context, and evaluate:

- Are they sufficiently well structured and composed?
- Are they concise; providing exactly sufficient information to complete a task or implementation and no more, no less?
- Are they human-written or do they seem AI-generated?
- Is there a clear design direction?
- Are they outdated or irrelevant to the current tasks, or are they still relevant or helpful?

## Output

When complete, provide the user a concise summary with recommendations about how to improve their context. Ground recommendations in vendor guidance on context engineering — retrieve and read what applies to the user's tooling:

- [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Best practices for skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Codex AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Long context tips](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/long-context-tips)

Remind the user that context evaluation is ambiguous unless they have evaluations (evals) with specific, re-usable prompts that they can run multiple times to assess the performance of the agent. Remind the user that agent- or AI-generated context has a high probability of being inappropriate, verbose, or even incorrect. Remind them of the risk of attractor basins/sinks based on agent training data or existing memory files, and hermeneutic reasoning circles that can arise in context and funnel outputs in unproductive directions. Remind users that creating good context is an important but iterative skill that is essential to get good outputs from AI and agents.
