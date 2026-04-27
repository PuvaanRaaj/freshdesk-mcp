# Freshdesk MCP

Clean-room Freshdesk MCP server that reads `FRESHDESK_API_KEY` and `FRESHDESK_DOMAIN` from the process environment at runtime.

The key point is that the MCP client config does not need to contain the API key. The server reads it internally when it starts.

## What This Covers

This server exposes Freshdesk tools for:

- tickets
- ticket conversations and replies
- automation rule switching for scheduled operations
- agents
- contacts
- companies

## Environment Variables

Set these in the operating system environment before starting the MCP server:

- `FRESHDESK_API_KEY`
- `FRESHDESK_DOMAIN`
- `FRESHDESK_TIMEOUT_SECONDS` (optional, defaults to `30`)

Examples for `FRESHDESK_DOMAIN`:

- `yourcompany.freshdesk.com`
- `https://yourcompany.freshdesk.com`

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

## macOS / Linux Setup

Set environment variables in the shell profile or launcher environment, then point your MCP client at the project:

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
