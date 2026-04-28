# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Forward Deployed Engineer take-home assignment** (Level 1). The task is to build a **Claims Processing System** for an insurance company that:

- Processes member claims with line items against coverage rules
- Determines what's covered, how much to pay, and tracks claim lifecycle
- Handles partial approvals (some line items approved, some denied)
- Explains why decisions were made

## Assignment Requirements

**Core functionality to build:**
- Claim submission with line items
- Coverage rule application and adjudication
- Claim lifecycle state machine (submitted → under review → approved/denied → paid)
- Decision explanations for members

**Required deliverables:**
- `app/` - Application code
- `docs/domain-model.md` - Entities, relationships, state machines
- `docs/decisions.md` - Trade-offs and assumptions
- `docs/self-review.md` - Honest self-assessment
- `ai-artifacts/` - AI chat exports and prompts
- `README.md` - Setup instructions

**Time budget:** 1 day

## Key Design Decisions (To Be Made)

The assignment intentionally leaves these open for candidate judgment:

- **Coverage rule representation** - Code, config, or DSL?
- **State machine design** - Claim-level vs line-item-level states
- **Partial approval handling** - When a claim has mixed outcomes
- **Limit tracking** - How to track used coverage against policy limits
- **Technology stack** - Candidate's choice

## Evaluation Criteria

1. **Domain decomposition** - Clean modeling of policies, claims, coverage rules
2. **Rule representation** - How coverage logic is structured
3. **State management** - Lifecycle tracking for claims and line items
4. **Edge case handling** - Partial approvals, limit exhaustion, retroactive changes
5. **Explanation capability** - System can explain WHY something was denied

## Constraints

- Must run locally
- Commit history must be preserved (submission is reviewed via git log)
- AI usage is required and must be documented in `ai-artifacts/`
- Code should be modifiable under pressure (next round is a 90-min pairing session)

## Notes for Future Claude Instances

This is an assessment project, not production code. Focus on:
- Demonstrating clear domain thinking over feature completeness
- Coherent abstractions that can be explained and modified
- Honest documentation of trade-offs over perfection

The candidate is expected to make decisions and justify them, not build a perfect system.
