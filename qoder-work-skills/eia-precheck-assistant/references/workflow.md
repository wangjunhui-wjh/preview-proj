# HB-PT Workflow Reference

## Task Setup

Create a task workspace with:

```text
project_files/       original user files
evidence/            downloaded or user-provided policy files
outputs/             node Markdown, JSON, and report files
logs/                search, extraction, and progress logs
.state/progress.md   resumable task status
```

Record:

- user request and project name if known
- uploaded files and hashes when possible
- active node
- completed nodes
- next node
- unresolved questions
- evidence candidates and verification status

## Node Sequence

### PREP-INGEST Project Dossier

Purpose: read original project materials and build a sourced project dossier.

Use when:

- the user uploads PDFs, images, scans, DOCX, spreadsheets, or free-form project text
- project facts are not yet structured

Do:

- inspect file types, page counts, text layers, images, tables, and unreadable files
- OCR/vision only where needed
- create a source index for key facts
- mark uncertainty and missing materials

Do not:

- decide EIA category
- decide compliance
- search the web for project facts

### HB-PT-000 Completeness And Module Selection

Purpose: judge whether materials are sufficient and select required modules.

Key outputs:

- completeness level
- can/cannot proceed
- critical missing information
- recommended modules
- priority supplement list

Stop or pause when:

- project identity, location, product/process, or construction content is too vague for downstream judgment
- uploaded files cannot be read and no pasted summary exists

### HB-PT-001 Project Profile

Purpose: normalize project facts into a structured profile.

Must include:

- project name, company, location, park/zone
- construction nature and content
- products, capacity, process, materials, equipment
- land use, investment, discharge destination, energy and water use
- pollution links and environmental risk clues

### HB-PT-002 Industry, EIA Category, Approval Path

Purpose: determine industry category, EIA category and likely approval route.

Evidence expectations:

- current EIA category management catalogue
- project product/process details
- local approval authority rules if available

If multiple categories may apply, list each possibility and what facts decide the path.

### HB-PT-003 Industrial Policy And Validity

Purpose: identify industrial policy fit, encouraged/restricted/eliminated risks, and policy validity.

Search official sources when policy basis is missing, old, conflicting, or validity is uncertain.

### HB-PT-004 Planning And Planning EIA Compliance

Purpose: check park/planning alignment and planning EIA constraints.

Evidence expectations:

- park master plan, planning EIA review opinion, industry access list, land-use planning
- uploaded park documents or official webpages

### HB-PT-005 Ecological Environment Zoning Control

Purpose: check ecological environment zoning, control unit and access requirements.

Evidence expectations:

- provincial/city ecological environment zoning results
- unit code/name if provided
- official control list or map evidence if available

### HB-PT-006 Yangtze River And Shoreline Control

Purpose: identify Yangtze River basin, shoreline, chemical park, drinking water source, and related control risks.

Only draw strong conclusions when location and official spatial evidence support them.

### HB-PT-007 Two-High Or Chemical Management

Purpose: identify "two high" or chemical project management risks.

Use product/process/energy/material information and current local/national requirements.

### HB-PT-008 Industry EIA Approval Principles

Purpose: map project to applicable industry EIA approval principles or technical review points.

If no applicable principle is found, state the gap instead of inventing a principle.

### HB-PT-009 Similar Projects And Pollution Controls

Purpose: find comparable projects and extract pollution links and typical control measures.

Do not treat similar projects as binding policy. Use them as engineering reference only.

### HB-PT-010 Comprehensive Report

Purpose: synthesize completed node outputs into a structured pre-judgment report.

Include:

- project overview
- module conclusions
- key risks
- missing materials
- evidence list
- recommended next actions

### HB-PT-011 Consistency Check

Purpose: audit contradictions across previous outputs.

Check:

- project facts consistency
- category/path consistency
- policy and planning evidence conflicts
- risk level conflicts
- missing source citations
- outdated or unverified evidence

## Auxiliary Tasks

### File Validation

Use `aux_file_validation.txt` to check whether uploaded files are readable, project-related, and usable for analysis.

### Independent Web Search

Use `aux_web_search.txt` when the user asks a standalone policy or evidence search question. Save URLs and candidate evidence status.

### Feedback Revision

Use `aux_feedback_revision.txt` when the user gives corrections or asks to revise a node. Re-evaluate affected downstream nodes.
