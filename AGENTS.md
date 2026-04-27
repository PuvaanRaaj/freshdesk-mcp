# AGENTS.md

## Purpose

This repository hosts a Freshdesk MCP server for:

- ticket operations
- issue and refund ticket discovery
- Freshdesk automation rule switching

## Setup Expectations

- Prefer a repo-local `.env` file for local development.
- Do not commit real Freshdesk credentials.
- Use `.env.example` as the template.

Required variables:

- `FRESHDESK_API_KEY`
- `FRESHDESK_DOMAIN`
- `FRESHDESK_TIMEOUT_SECONDS` optional

## Development Rules

- Keep the MCP tool surface small and explicit.
- Prefer adding thin convenience tools on top of documented Freshdesk API fields.
- Avoid embedding production credentials or customer data in tests or docs.
- Keep search helpers aligned to Freshdesk's field-based search API.
- For automation rule changes, preserve the current day/night mapping unless the user explicitly asks to change it.

## Validation

Run:

```bash
uv sync
uv run python -m unittest discover -s tests -p 'test_*.py'
```

## Important Files

- `src/freshdesk_mcp/server.py`: MCP tool definitions
- `src/freshdesk_mcp/config.py`: config and `.env` loading
- `tests/`: unit tests
- `README.md`: user-facing setup and usage
- `AUTOMATIONS.md`: scheduler and shift-switching notes
