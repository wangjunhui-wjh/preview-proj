# Evidence And Knowledge Rules

## Allowed Evidence

Use only:

- user-uploaded project files
- user-pasted project text
- OCR/vision output tied to a specific file/page/image
- user-uploaded policy or planning files
- official webpages or downloadable policy files accessed during the task
- verified local knowledge base files with metadata and source path

## Disallowed Evidence

Do not use as final basis:

- model memory alone
- search snippets without opening the source
- unofficial reposts when an official source is available
- webpages with no source, issuer, date, or document identity
- hallucinated clause numbers or document numbers

## Web Search Practice

Let the agent formulate searches based on:

- project location
- industry/product/process
- park/zone name
- target node
- missing evidence
- official issuing bodies

Prefer official domains:

- national ministries and commissions
- provincial/city/district governments
- ecological environment departments
- development and reform departments
- natural resources departments
- park management committees
- official standard and regulation platforms

## Candidate To Verified Evidence

Classify evidence:

```text
candidate           found but not validated
verified_candidate  source looks reliable and original text is saved, awaiting human confirmation
verified            manually or rule-confirmed for formal use
rejected            unrelated, unreliable, duplicate, inaccessible, or unverifiable
deprecated          replaced, repealed, expired, or no longer current
```

Formal conclusions should prioritize `verified`. If only `verified_candidate` exists, explicitly write that manual verification is recommended. Ordinary `candidate` evidence can guide investigation but should not support strong final conclusions.

## Minimum Citation Fields

For each cited source, capture as many fields as possible:

- title
- issuer
- document number
- publication date
- effective date
- validity status
- URL or local file path
- retrieved time
- page/section/clause if known
- hash or saved snapshot path when available

If a cited source lacks clause-level support, write that the clause is not available instead of inventing it.

## Policy Validity Checks

When policy validity matters, check:

- file name and document number
- issuing authority
- publication and implementation date
- validity period
- repeal or replacement notices
- newer documents with same subject
- conflict between national, provincial, city, and park-level rules

If uncertain, write `有效性待核实，建议人工确认`.
