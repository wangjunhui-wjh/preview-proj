# Dual Edition Implementation State

- objective: build desktop and private-server editions from one shared codebase
- principle: use Hermes native Agent, tool, vision, web, approval and Docker terminal capabilities; do not reimplement them in FastAPI
- current_step: DUAL-02
- next_step: DUAL-03_desktop_edition
- status: shared_runtime_hardening_complete
- updated_at: 2026-07-19 Asia/Shanghai

## Steps

| Step | Status | Acceptance |
| --- | --- | --- |
| DUAL-01 | complete | Plan, architecture boundary, risk treatment and acceptance rules documented |
| DUAL-02 | complete | Shared backend/runtime hardening complete |
| DUAL-03 | pending | Desktop edition complete |
| DUAL-04 | pending | Private server edition complete |
| DUAL-05 | pending | Operations/security/package hardening complete |
| DUAL-06 | pending | Both editions pass acceptance |
| DUAL-07 | pending | Final docs and recovery state complete |

## Recovery

After context compaction, read in order:

1. `.state/progress.md`
2. `.state/dual_edition_plan.md`
3. `logs/dual_edition_20260719.md`
4. `outputs/双版本系统实施计划与验收标准.md`
