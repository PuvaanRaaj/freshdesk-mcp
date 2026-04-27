# Freshdesk MCP

Freshdesk MCP server for ticket operations, issue discovery, and automation-rule switching.

The server reads `FRESHDESK_API_KEY` and `FRESHDESK_DOMAIN` from process environment variables and also supports loading them from a local `.env` file.

## What This Covers

This server exposes Freshdesk tools for:

- tickets
- ticket conversations and replies
- issue and refund ticket discovery
- automation rule switching for scheduled operations
- agents
- contacts
- companies

## Configuration

The server looks for these values at startup:

- `FRESHDESK_API_KEY`
- `FRESHDESK_DOMAIN`
- `FRESHDESK_TIMEOUT_SECONDS` (optional, defaults to `30`)

Examples for `FRESHDESK_DOMAIN`:

- `razer-support`
- `yourcompany.freshdesk.com`
- `https://yourcompany.freshdesk.com`

### Option 1: `.env` File

You can keep the credentials in a `.env` file at the repo root. Start from [.env.example](/Users/puvaan.shankar/programming/freshdesk-mcp/.env.example):

```dotenv
FRESHDESK_API_KEY=your_api_key
FRESHDESK_DOMAIN=razer-support
FRESHDESK_TIMEOUT_SECONDS=30
```

When you start `freshdesk-mcp`, it will load that `.env` file automatically.

If `FRESHDESK_DOMAIN` is a bare subdomain such as `razer-support`, the server expands it to `https://razer-support.freshdesk.com`.

### Option 2: Shell Environment

If you prefer shell variables:

```bash
export FRESHDESK_API_KEY="your_api_key"
export FRESHDESK_DOMAIN="razer-support"
export FRESHDESK_TIMEOUT_SECONDS="30"
```

For production or shared machines, shell environment or secret management is still the cleaner option.

## Windows Setup For Non-Technical Users

This is the simplest approach for an ops team using Windows and Claude Desktop.

### 1. Install Python and uv

Install:

- Python 3.11+
- `uv` from [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

### 2. Put This Project In A Stable Folder

Example:

```text
C:\Tools\freshdesk-mcp
```

### 3. Set User Environment Variables In Windows

Open:

`Start` -> `Edit environment variables for your account`

Add:

- `FRESHDESK_API_KEY` = your real Freshdesk API key
- `FRESHDESK_DOMAIN` = yourcompany.freshdesk.com

Then fully restart Claude Desktop after setting them.

### 4. Claude Desktop Config On Windows

Use the wrapper script so the config file contains no secret:

```json
{
  "mcpServers": {
    "freshdesk": {
      "command": "C:\\Tools\\freshdesk-mcp\\scripts\\run_freshdesk_mcp.cmd"
    }
  }
}
```

### 5. First-Time Dependency Install

From PowerShell in the project folder:

```powershell
uv sync
```

After that, Claude Desktop can launch the server through the `.cmd` wrapper.

## Claude Desktop Setup

### macOS / Linux

```json
{
  "mcpServers": {
    "freshdesk": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/freshdesk-mcp", "run", "freshdesk-mcp"]
    }
  }
}
```

### Windows

Use the wrapper script:

```json
{
  "mcpServers": {
    "freshdesk": {
      "command": "C:\\Tools\\freshdesk-mcp\\scripts\\run_freshdesk_mcp.cmd"
    }
  }
}
```

## Codex Setup

Codex supports the same server through local MCP registration.

### Codex CLI Registration

Make sure the repo root contains a `.env` file first. You can copy [.env.example](/Users/puvaan.shankar/programming/freshdesk-mcp/.env.example):

```dotenv
FRESHDESK_API_KEY=your_api_key
FRESHDESK_DOMAIN=razer-support
FRESHDESK_TIMEOUT_SECONDS=30
```

Then register the MCP server without repeating the secrets on the command line:

```bash
codex mcp add freshdesk \
  -- uv --directory /absolute/path/to/freshdesk-mcp run freshdesk-mcp
```

Then verify:

```bash
codex mcp list
codex mcp get freshdesk
```

Once Codex starts a new session with the `freshdesk` MCP loaded, it should call the MCP tools directly. If the MCP is not loaded in the current session, Codex may fall back to shell exploration and direct scripts, which produces much noisier step-by-step output.

### Codex Config File

You can also add it directly to `~/.codex/config.toml` and still rely on the repo-local `.env` file:

```toml
[mcp_servers.freshdesk]
command = "uv"
args = ["--directory", "/absolute/path/to/freshdesk-mcp", "run", "freshdesk-mcp"]
```

## Local Development

Install dependencies:

```bash
uv sync
```

Run the server:

```bash
uv run freshdesk-mcp
```

## Available Tools

- `create_ticket`
- `update_ticket`
- `delete_ticket`
- `search_tickets`
- `search_tickets_by_type`
- `search_tickets_by_tag`
- `search_tickets_by_date_range`
- `find_refund_tickets`
- `get_ticket_fields`
- `get_tickets`
- `get_ticket`
- `get_automation_rule`
- `update_automation_rule`
- `switch_assignment_shift`
- `get_ticket_context`
- `get_ticket_conversation`
- `create_ticket_reply`
- `create_ticket_note`
- `update_ticket_conversation`
- `view_ticket_summary`
- `update_ticket_summary`
- `delete_ticket_summary`
- `get_agents`
- `view_agent`
- `create_agent`
- `update_agent`
- `search_agents`
- `list_contacts`
- `get_contact`
- `search_contacts`
- `update_contact`
- `list_companies`
- `view_company`
- `search_companies`
- `find_company_by_name`
- `list_company_fields`

## Automation Tools

This repo now includes Freshdesk automation-rule tools for scheduled shift switching:

- `get_automation_rule`
- `update_automation_rule`
- `switch_assignment_shift`

`switch_assignment_shift` encodes the day/night preset you described for these six rules:

- `51001008328` Helpdesk Morning Ticket
- `51001005307` Helpdesk Evening New Ticket
- `51001020738` Ticket Auto-Unassigned from OOO Agent (5pm-2am)
- `51000234971` Ticket Auto-Unassigned from OOO Agent (9am-6pm)
- `51000234972` Reopen Ticket Rules for Working Hours (9am-6pm)
- `51001017301` Reopen Ticket Rules for Extended Hours (5pm-2am)

Example:

```text
Run freshdesk.switch_assignment_shift with shift="night"
```

## Ticket Search Helpers

This repo now includes higher-level search helpers for issue-oriented ticket discovery:

- `search_tickets_by_type`
- `search_tickets_by_tag`
- `search_tickets_by_date_range`
- `find_refund_tickets`

Examples:

```text
Use freshdesk.find_refund_tickets with status=2.
```

```text
Use freshdesk.search_tickets_by_type with issue_type="payment_failed" and status=2.
```

```text
Use freshdesk.search_tickets_by_tag with tag="chargeback" and status=3.
```

```text
Use freshdesk.search_tickets_by_date_range with field_name="created_at", start_date="2026-04-01", end_date="2026-04-30".
```

These helpers map to Freshdesk's field-based search API. In practice, refund or issue searches work best when your support process consistently uses the built-in `type` field or tags.

## Scheduler Setup Guides

See [AUTOMATIONS.md](/Users/puvaan.shankar/programming/freshdesk-mcp/AUTOMATIONS.md) for practical setup notes for:

- Claude Cowork scheduled tasks
- Codex automations
- choosing between local Claude Desktop MCP and remote Cowork connectors

## Contributors

See [CONTRIBUTORS.md](/Users/puvaan.shankar/programming/freshdesk-mcp/CONTRIBUTORS.md).

## Security Notes

This keeps the API key out of the repo and out of the MCP client JSON config.

It does not create a hard security boundary against a coding agent that already has shell or process-level access to the same machine. That stronger requirement needs a separate proxy service.
