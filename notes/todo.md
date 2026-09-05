# AI Companion To-Do

Updated: 2026-08-17

## Fixed Now

- [x] Keep scheduled extraction inside the message snapshot that triggered it.
- [x] Make idle and forced-backlog callers match `run_memory_extraction_batch()`.
- [x] Prevent the manual extraction endpoint from acquiring the extraction lock twice.
- [x] Return created candidate IDs to the manual extraction endpoint.
- [x] Reset extraction progress when conversation history is cleared.
- [x] Remove message source links before clearing history so foreign keys do not block deletion.

## Finish Day 12

- [ ] Add normalized exact duplicate filtering for existing memories, existing candidates, and proposals in the same extraction result.
- [ ] Add two older context messages to each extraction window while only allowing new-batch IDs as evidence.
- [ ] Decide whether the first scheduler run should backfill existing chat history or initialize the watermark at the latest message.
- [ ] Add extraction status (`idle`, `scheduled`, `running`, `failed`) to the developer API and panel.
- [ ] Poll or refresh candidates after background extraction completes instead of only immediately after `/chat`.
- [ ] Run the ten Day 12 memory scenarios and record expected versus proposed memories in a test log.

## Reliability Later

- [ ] Store a batch's candidates and updated watermark in one SQLite transaction so a crash cannot create duplicate candidates on retry.
- [ ] Decide how failed extraction batches should be retried and shown in the developer panel.
- [ ] Keep the current in-process `Timer` and `Lock` scheduler limited to one Uvicorn worker.
- [ ] Replace the in-process scheduler with a persistent job queue before using multiple workers or treating extraction as production-critical.
- [ ] Evaluate `SMALL_MODEL` for extraction after collecting quality and latency results from the Day 12 test log.
