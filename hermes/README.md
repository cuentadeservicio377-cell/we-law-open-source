# Hermes Layer

Hermes is the Managing Partner layer of We Law OS. This directory documents how Hermes should use the public `skills/`, `config/`, `schemas/` and `workspace/brain/` directories.

In a live deployment Hermes should:

- receive instructions from chat or dashboard;
- resolve client and matter context;
- read the Legal Brain before routing;
- create command records and matter briefs;
- delegate to Paperclip workers;
- check Workspace state;
- report blockers and approval requests to the lawyer.

The public repo does not bundle Hermes itself. Install Hermes separately and point it at this repository.

## Suggested Local Layout

Point the Hermes profile working directory at this repository root. Then expose these directories to Hermes:

- `skills/` for We Law skills.
- `config/` for role contracts and command spine.
- `schemas/` for structured payloads.
- `workspace/brain/` for Legal Brain memory.

Verification goal: Hermes should be able to read `skills/hermes-welaw-core/SKILL.md`, resolve the Legal Brain, and prepare a command record before delegating anything to Paperclip.
