# Issue tracker

Issues for this repo live as **local markdown files** under `.scratch/<feature>/`.

## Structure

Each feature or epic gets its own subdirectory:

```
.scratch/
  user-authentication/
    001-issue.md
    002-issue.md
  booking-flow/
    001-issue.md
```

## File format

Each issue is a markdown file with YAML frontmatter:

```markdown
---
title: Brief title
status: needs-triage | needs-info | ready-for-agent | ready-for-human | wontfix | done
labels: [bug, enhancement, etc.]
created: YYYY-MM-DD
---

Description of the issue...
```

## Workflow

- **Creating issues**: `to-tickets` and similar skills write new files under `.scratch/<feature>/`
- **Reading issues**: Skills glob `.scratch/**/*.md` and parse frontmatter
- **Updating status**: Edit the `status:` field in frontmatter
- **Closing issues**: Set `status: done` or move to an archive subdirectory

## PRs as a request surface

**Disabled.** External pull requests are not monitored as an issue intake surface for this repo.
