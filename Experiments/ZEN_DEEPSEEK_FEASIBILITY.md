# OpenCode Zen / DeepSeek feasibility record

**Status:** not eligible for an analytic cell.

## 2026-08-19 smoke

- Installed OpenCode version: 1.18.18.
- Zen model catalog exposed `deepseek-v4-flash-free` through the OpenAI-compatible
  `/chat/completions` endpoint.
- A direct short package-list request succeeded as `deepseek-v4-flash-free`, finish reason
  `stop`, with non-empty final content.
- The repository harness then completed four code calls using the frozen prompts and caps.
  The gateway reported 4,307 completion tokens, but all four assistant `content` strings were
  empty. The legacy smoke preceded per-response metadata sidecars, so the original response
  bodies cannot establish whether tokens occupied a provider-specific reasoning field.
- The first package query then failed after five retries with HTTP 429
  `FreeUsageLimitError`. The exact record is
  `Tests/smoke_zen_deepseek-v4-flash-free_Python/LLM_Recent_packages_1.json.errors.json`.
- Zen's OpenAI-compatible endpoint does not accept the experiment's `top_k=20`; the manifest
  records that adjustment.

## 2026-08-25 follow-up

A single direct replay of the exact first code prompt was attempted solely to inspect final
content versus any provider-specific reasoning field. The request failed before generation
with a local authentication/connection error, so it produced no response and no billable
usage. No additional retries or paid Zen cells were launched.

## Decision

The limited-time free endpoint is not reproducible enough for a 2,400-call cell: it exhausted
free usage after four long calls, failed to produce inspectable final content in those calls,
and cannot preserve `top_k`. OpenCode itself must not be used as the experimental interface
because its coding-agent wrapper changes prompts and behavior. A future Zen study would need:

1. a stable paid or research quota;
2. a raw API smoke with ordered finish/content/reasoning metadata;
3. a preregistered `top_k` deviation; and
4. a separate inferential family.

Given the active Kimi K3 successor experiment and the $100 aggregate budget, Zen receives no
further spend in this iteration.
