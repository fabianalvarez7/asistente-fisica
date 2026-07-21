# Proposal: Socratic Layer

## Intent

The current system answers questions directly from the corpus. The Socratic layer transforms it into a pedagogical tool that guides students with questions, never giving the solution — the prototype's core differentiator.

## Scope

### In Scope
- Extend `SYSTEM_PROMPT` with Socratic instructions (wrap approach — preserve RAG grounding)
- Progressive hint ladder: 3 levels (conceptual → specific → near-answer), never the final numerical answer
- 3 few-shot examples in Rioplatense voseo, injected as messages in the Groq call
- Edge cases: "dame la respuesta" → progressive hint; wrong answers → flag + repreguntar; off-topic → preserve refusal
- Single-turn only — no conversation history tracking

### Out of Scope
- Student history in SQLite, identification/login (separate cycles)
- Multi-turn Socratic scaffolding (requires history — deferred)
- Dashboard, model/embedding/infrastructure changes
- RAG retrieval logic changes

## Capabilities

### New Capabilities
- `socratic-guidance`: Pedagogical behavior — hint ladder, intervention levels, error handling, edge cases

### Modified Capabilities
None — RAG grounding preserved via wrap approach.

## Approach

Wrap existing system prompt (Approach B, explore.md §3). Inject 3 few-shot examples as messages (explore.md §5). ~47 lines across 3 files.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `rag/prompts/chat_prompt.py:10-20` | Modified | +Socratic instructions (~30 lines) |
| `rag/chain.py:73-82` | Modified | +Few-shot message injection (~15 lines) |
| `rag/prompts/__init__.py` | Modified | Export few-shot list (~2 lines) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Model ignores Socratic instructions | High | Few-shot + temperature=0.0; test 10+ queries |
| Single-turn feels shallow | High | Acknowledged — true Socratic needs history (next cycle) |
| Breaking existing demo | Medium | Wrap preserves grounding; test 8 demo queries |
| Few-shot topic bias | Medium | Topic-agnostic examples |

## Rollback Plan

Git revert `chat_prompt.py` and `chain.py`. No database/infra changes.

## Dependencies

None — prompt-only change.

## Success Criteria

- [ ] Assistant asks guiding questions, never gives direct answers (10+ test queries)
- [ ] Never gives final numerical answer ("dame la respuesta" scenarios)
- [ ] Progressive hint ladder works (stuck student scenarios)
- [ ] No regression on 8 demo queries
- [ ] Off-topic/out-of-scope still get hardcoded refusal
- [ ] Nair validates pedagogical behavior

## Open Questions

1. Few-shot source: invented vs. cuadernillo exercises? (explore.md §8.5)
2. When corpus expands, update examples? (explore.md §8.4)
3. Document "pista máxima" as hard spec rule? (product-decisions #1)

## References

- `openspec/changes/socratic-layer/explore.md`
- Engram `sdd/socratic-layer/product-decisions` (id 89)
- Engram `sdd/socratic-layer/scope` (id 87)
- `AGENTS.md` §3, §7, §8
