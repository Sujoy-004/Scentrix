---
name: gsd-verify-work
description: "Validate built features through conversational UAT"
---

<objective>
Validate built features through conversational testing with persistent state.

Purpose: Confirm what the agent built actually works. Before presenting any UAT question or verification checkpoint to the user, you MUST inspect the codebase, local test states, and the AST/graph definitions inside `graphify-out` (which is updated after every turn) to programmatically answer the question yourself. Only prompt the user for confirmation if a physical visual interaction is strictly required and cannot be verified via files or local commands. One test at a time, plain text responses, no interrogation. When issues are found, automatically diagnose, plan fixes, and prepare for execution.

Output: {phase_num}-UAT.md tracking all test results. If issues found: diagnosed gaps, verified fix plans ready for /gsd-execute-phase
</objective>

<execution_context>
@.agent/get-shit-done/workflows/verify-work.md
@.agent/get-shit-done/templates/UAT.md
</execution_context>

<context>
Phase: $ARGUMENTS (optional)
- If provided: Test specific phase (e.g., "4")
- If not provided: Check for active sessions or prompt for phase

Context files are resolved inside the workflow (`init verify-work`) and delegated via `<files_to_read>` blocks.
</context>

<process>
Execute end-to-end.
Preserve all workflow gates (session management, test presentation, diagnosis, fix planning, routing).
</process>
