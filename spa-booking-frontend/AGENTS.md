<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Agent skills

### Issue tracker

Issues are tracked as markdown files under `.scratch/<feature>/` in this repo. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout: one `docs/CONTEXT.md` (canonical domain glossary) and `docs/adr/` (Architectural Decision Records). Read `docs/CONTEXT.md` first when starting any feature. Update it when introducing new domain concepts. Write a new ADR for significant architectural decisions.

**Enforcement**: Update `docs/CONTEXT.md` as part of every feature PR. If a PR touches domain entities, business rules, or the booking flow, the domain doc must reflect it. CI should reject PRs that introduce domain changes without corresponding doc updates.
