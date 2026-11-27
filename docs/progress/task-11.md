# Task 11 — RAG configuration and customer advice

**Status:** Completed locally on 2026-11-27. The chatbot on port 8001 was restarted with the updated Python code.

## Implementation

- Kept the existing Markdown loader, heading-based chunking, `all-MiniLM-L6-v2` embedding model, PostgreSQL pgvector store, and incremental indexer. The configured model generates 384-dimensional vectors; the live `knowledge_chunks.embedding` column is `vector(384)` with a cosine IVFFlat index.
- Corrected the sole indexed knowledge document, `docs/knowledge/faq.md`. Removed unsupported fixed hours, mobile-app, cancellation fee window, treatment examples, and private-room claims. Added only documented booking guidance and explicit limits for unknown policies, room facilities, and medical advice. The final file was re-indexed as seven chunks under `general-faq`.
- FAQ retrieval still ranks by cosine similarity and filters below the configured 0.35 score, then requires the question's specific terms to occur in an excerpt. At most two answerable chunks are used and cited. Unmatched questions receive a clear unknown answer. The no-key path returns only an answerable excerpt; the LLM path receives selected excerpts under a dedicated system instruction that treats them as untrusted data. Generated live booking codes, prices, or dated availability claims are rejected in favor of the verified excerpt.
- Questions about current shop hours, catalog services, and prices use Flask's shop and course tools without changing the booking draft. Booking confirmation questions use the existing verified booking lookup. Availability, service options, price validation, and booking writes remain with Flask.
- Separated runtime pgvector connections from offline schema creation. Runtime checks existing columns and vector dimension without DDL and uses autocommit for searches. The indexer skips redundant column and index DDL. This removed a measured lock wait: a fresh runtime connection had waited on `ALTER TABLE` while the older server held an idle read transaction.

## Verification

- Chatbot suite: **300 passed** using a temporary asyncio pytest runner because the installed `pytest-asyncio` is incompatible with the installed pytest. No runtime dependency was changed. `compileall` and `git diff --check` passed.
- PostgreSQL pgvector version **0.8.7**; the configured model produced `(1, 384)` and the table uses `vector(384)`. The corrected FAQ was re-indexed in the existing database. Read-only retrieval checks selected the cancellation and group answers and rejected unrelated price and medical matches.
- Local Redis returned `PONG`; the running chatbot health endpoint returned `{"status":"ok"}`. The updated code was exercised against Redis and pgvector: it cited only the cancellation FAQ for a cancellation question, gave an explicit medical uncertainty answer for an unsupported arthritis claim, and stated that private couples rooms are undocumented. Live shop hours and catalog prices in updated-code answers matched Flask API responses. After the local server restart, the same FAQ results were verified through `/chat` on port 8001.

## Runtime boundary

The local `chatbot/.env` has `CHATBOT_PG_DSN` but no effective `CHATBOT_OPENAI_API_KEY`, so the live FAQ uses the cited-excerpt path. The LLM grounding path was verified with a mocked model response; no external LLM call was made.
