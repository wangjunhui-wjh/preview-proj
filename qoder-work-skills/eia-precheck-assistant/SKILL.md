---
name: eia-precheck-assistant
description: AI-assisted Chinese environmental impact assessment pre-study workflow for construction projects. Use when Qoder Work should analyze project materials, PDFs, scanned documents, images, policy evidence, web search results, EIA category, planning/zoning compliance, Yangtze River controls, two-high/chemical controls, approval principles, similar projects, comprehensive reports, consistency checks, feedback revisions, or run the current 环评前期研判AI助手 HB-PT prompt system as a skill.
version: 1.0.0
---

# 环评前期研判 AI 助手

Use this skill to perform early-stage EIA pre-judgment for Chinese construction projects with the same workflow as the current `环评前期研判AI助手` system.

## Core Rules

1. Treat all outputs as AI-assisted preliminary judgments. Always require review by a qualified EIA engineer.
2. Never invent project facts, policy titles, document numbers, clauses, approval authorities, zoning results, red-line status, discharge destinations, energy data, or precedent conclusions.
3. Use only traceable sources: user-provided project materials, readable uploaded files, OCR/vision findings, verified local knowledge files, or real web URLs accessed during the task.
4. If evidence is missing, write `资料不足，建议人工核实` instead of filling gaps with experience.
5. For PDFs, first inspect text layer and structure. Use OCR/vision only for scanned pages, images, figures, drawings, signatures, tables, screenshots, or pages with insufficient text.
6. Let the agent organize web searches. Do not rely on user-supplied fixed search keywords unless the user explicitly gives them as constraints.
7. Search findings are candidate evidence until official source, publication metadata, validity, and local snapshot are checked.
8. Do not reveal hidden chain-of-thought. Show concise progress, tool actions, searched URLs, read files, intermediate conclusions, uncertainty, and final reasoning summary.

## Standard Workflow

Run nodes in this order unless the user asks for a specific node:

```text
PREP-INGEST
HB-PT-000
HB-PT-001
HB-PT-002
HB-PT-003
HB-PT-004
HB-PT-005
HB-PT-006
HB-PT-007
HB-PT-008
HB-PT-009
HB-PT-010
HB-PT-011
```

Use `references/workflow.md` for node responsibilities, inputs, and stop conditions.

## How To Execute

1. Create or identify a task folder for all source files, notes, outputs, downloaded policy files, and logs.
2. Read project materials through `PREP-INGEST` before specialized judgment. Build a project dossier with source indexes.
3. Run `HB-PT-000` to decide whether information is sufficient and which modules should be started.
4. Run specialized HB nodes only when needed by `HB-PT-000`, user instruction, or project risk.
5. For each node, load the corresponding prompt from `references/prompts/`.
6. Write each node result as a Markdown-style report and include a compact JSON block when possible.
7. Preserve provenance: file name, page/image/table location, URL, retrieved time, policy title, document number, issuer, publication date, and validity status.
8. When revising from user feedback, use `references/prompts/aux_feedback_revision.txt`, rerun the affected node, and mark downstream nodes that may need refresh.

## Required Output Shape

For every node output:

- Start with a direct conclusion and risk level.
- Separate project facts, evidence, preliminary judgment, uncertainty, missing materials, and manual review points.
- Include source references for every material conclusion.
- End with the required disclaimer from the node prompt.

Use `templates/node-result.md` for ordinary node output and `templates/final-report.md` for comprehensive reports.

## Evidence And Knowledge Base

Use `references/evidence.md` when searching, downloading, validating, or citing policies. Key rule: formal conclusions should prefer official and verified sources. Search snippets or unverified reprints are clues, not final evidence.

## Prompt Assets

All current prompt files are in `references/prompts/`. Load only the prompt needed for the current node:

- `system_prompt.txt`: global role and evidence rules.
- `prep_ingest_project_dossier.txt`: project dossier extraction.
- `hb_pt_000_completeness.txt` through `hb_pt_011_consistency.txt`: node prompts.
- `aux_file_validation.txt`: uploaded material validity check.
- `aux_web_search.txt`: independent web search task.
- `aux_feedback_revision.txt`: feedback-based correction.

## Long Task Discipline

For long unattended work, maintain:

```text
.state/progress.md
logs/
outputs/
```

After each step or node finishes, update `.state/progress.md` with `current_step`, `next_step`, status, timestamp, and key artifacts. If context is compacted or interrupted, first read `.state/progress.md`, recent `logs/`, and latest `outputs/`, then continue from `next_step`.
