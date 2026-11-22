# Chatbot knowledge base

The chatbot uses Markdown files under `docs/knowledge` for informational answers. Booking creation, availability, status, cancellation, and modification continue through backend tools.

## Configure

Provide PostgreSQL with the `vector` extension available, then set `CHATBOT_PG_DSN` for both the indexing command and chatbot. The database user needs permission to create the extension and table on first use, or an administrator can create the extension ahead of time. The default embedding model is `all-MiniLM-L6-v2` (384 dimensions); use the same `CHATBOT_EMBEDDING_MODEL` and `CHATBOT_EMBEDDING_DIM` for indexing and chat.

Optional settings: `CHATBOT_KNOWLEDGE_ROOT` (default `docs/knowledge`), `CHATBOT_CHUNK_SIZE` (500), `CHATBOT_CHUNK_OVERLAP` (50), `CHATBOT_VECTOR_STORE_TOP_K` (5), and `CHATBOT_VECTOR_STORE_MIN_SCORE` (0.35). `CHATBOT_OPENAI_API_KEY` enables concise grounded answers; without it, the chatbot returns a matching excerpt and source.

Install `chatbot/requirements.txt`, then run from the repository root:

```sh
python3 -m chatbot.scripts.index_knowledge_base
```

Re-running embeds only changed documents. Add or edit Markdown files to update them. Delete an entry by ID with `python3 -m chatbot.scripts.index_knowledge_base --delete-document general-faq`. Use `--prune` to remove indexed `source: file` documents deleted from the chosen knowledge root. This only affects that root.

## Document format

```markdown
---
document_id: service-full-body
title: Full Body Massage
category: services
shop_id: 2
language: en
source: file
active: true
---

# Full Body Massage

Write verified shop information here.
```

`document_id` is a stable ID used for updates and deletion. When omitted, the absolute file path is used. `shop_id` is optional; omit it for content shared by all shops. `active: false` keeps an entry indexed but excludes it from normal retrieval. Headings are kept with each chunk and shown in source citations. The indexer accepts FAQ and business documents in the same directory.
