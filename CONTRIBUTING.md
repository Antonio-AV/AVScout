# Contributing

## Branches

Use one branch per issue. When creating a branch manually, use:

```text
<type>/<ticket-or-description>
```

Examples:

```text
feat/AVS-123-player-search
fix/AVS-124-filter-boundary
```

When Orca provides an existing issue branch, keep that branch name.

## Commits

Use Conventional Commits:

```text
<type>(<scope>): <imperative description>
```

Valid types are `feat`, `fix`, `docs`, `style`, `refactor`, `test`, and `chore`.
Keep the subject under 72 characters. Add a body for non-trivial changes and
explain why the change is needed rather than restating the diff.

Create commits at coherent milestones, not for every small edit. Never commit
secrets, generated files, raw datasets, local databases, or failing work.

## Pull Requests

Pull requests should be small, focused, and linked to their Linear issue. Use the
repository pull request template. Use a Conventional Commit-style title:

```text
<type>(<scope>): <imperative description>
```

Keep the title under 72 characters and include:

- A concise summary and motivation.
- The acceptance criteria and their status.
- Commands used for validation.
- Known risks, limitations, and follow-up work.

Run `npm run quality` before pushing. Review the complete diff yourself before
requesting review. At least one approval is required before merge. Do not merge a
pull request while required CI checks are failing.

## Local Development

Install dependencies from the repository root:

```bash
uv sync --project backend --dev
npm ci
```

Run the complete merge gate with:

```bash
npm run quality
```

Use `npm run frontend:dev` and
`uv run --project backend --dev python backend/run.py` to start the applications.

Keep `package-lock.json` and `backend/uv.lock` synchronized with dependency
changes. Do not edit lockfiles manually.
