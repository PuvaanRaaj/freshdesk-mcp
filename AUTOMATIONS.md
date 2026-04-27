# Freshdesk Shift Automation Setup

This repo can now drive the same shift-switching behavior as your Google Apps Script by updating Freshdesk automation rules directly through MCP.

## What Changed

Three automation-related MCP tools are available:

- `get_automation_rule(automation_type, rule_id)`
- `update_automation_rule(automation_type, rule_id, active)`
- `switch_assignment_shift(shift)`

`switch_assignment_shift` is the high-level tool that maps your current script into two presets:

- `shift="night"`:
  turns on evening and extended-hours rules, and turns off morning and working-hours rules
- `shift="day"`:
  turns on morning and working-hours rules, and turns off evening and extended-hours rules

The preset currently updates these six rules:

- `1 / 51001008328` Helpdesk Morning Ticket
- `1 / 51001005307` Helpdesk Evening New Ticket
- `4 / 51001020738` Ticket Auto-Unassigned from OOO Agent (5pm-2am)
- `4 / 51000234971` Ticket Auto-Unassigned from OOO Agent (9am-6pm)
- `4 / 51000234972` Reopen Ticket Rules for Working Hours (9am-6pm)
- `4 / 51001017301` Reopen Ticket Rules for Extended Hours (5pm-2am)

## What This Means Technically

Yes, you can set up an automation to run the work item logic.

You are not triggering Freshdesk's own built-in time rules directly. Instead, your scheduled agent would call MCP and tell Freshdesk to update the `active` state of those rules at the right time, which is exactly what your Apps Script does today with direct REST calls.

So the flow becomes:

1. scheduler fires at the planned time
2. Claude Cowork or Codex calls `switch_assignment_shift("day")` or `switch_assignment_shift("night")`
3. this MCP server sends six `PUT /api/v2/automations/{type}/rules/{id}` requests to Freshdesk
4. Freshdesk starts using the newly active rules for ticket assignment and reopen handling

## Claude Desktop Local MCP Setup

This is the local setup for testing and manual runs.

1. Install dependencies:

```bash
uv sync
```

2. Set environment variables on the machine that will run Claude Desktop:

```bash
export FRESHDESK_API_KEY="your_api_key"
export FRESHDESK_DOMAIN="razer-support"
```

The bare subdomain form is supported and resolves to `https://razer-support.freshdesk.com`.

3. Add the MCP server to Claude Desktop.

macOS or Linux:

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

Windows:

```json
{
  "mcpServers": {
    "freshdesk": {
      "command": "C:\\Tools\\freshdesk-mcp\\scripts\\run_freshdesk_mcp.cmd"
    }
  }
}
```

4. Restart Claude Desktop.

Manual test prompt:

```text
Use freshdesk.get_automation_rule with automation_type=1 and rule_id=51001008328. Then use freshdesk.switch_assignment_shift with shift="night".
```

## Claude Cowork Scheduler

Claude Cowork scheduled tasks can run this logic, but only if the Freshdesk MCP is available as a remote connector.

Your current local `uv run freshdesk-mcp` process is not enough for Cowork scheduled tasks because Cowork connectors must be reachable from Anthropic's cloud.

### Required Architecture For Cowork

1. Host this MCP server at a public HTTPS endpoint.
2. Put authentication in front of it.
3. Add it in Claude through `Customize > Connectors`.
4. Enable that connector in the Cowork task.
5. Schedule two tasks:
   one for `night`
   one for `day`

### Suggested Cowork Tasks

Night switch task prompt:

```text
Use the Freshdesk connector and run switch_assignment_shift with shift="night". After the update, summarize which rules were turned on and off.
```

Day switch task prompt:

```text
Use the Freshdesk connector and run switch_assignment_shift with shift="day". After the update, summarize which rules were turned on and off.
```

Recommended schedule based on your script:

- weekday evening run: around `5:30 PM`
- weekday early-morning run: around `1:50 AM`

If you want the exact old behavior, keep the same weekday windows your Apps Script used:

- night trigger window: Monday to Friday, `17:30` to `17:34`
- day trigger window: Tuesday to Saturday, `01:50` to `01:54`

## Codex Automations

Codex can run this directly against the repo without deploying a remote connector, as long as the Codex workspace has access to the same environment variables and MCP setup.

The clean way to model it is with two cron automations:

1. a `night` automation
2. a `day` automation

Suggested `night` prompt:

```text
Run the Freshdesk MCP tool switch_assignment_shift with shift="night". Return a short confirmation of the six rules updated and their target active states.
```

Suggested `day` prompt:

```text
Run the Freshdesk MCP tool switch_assignment_shift with shift="day". Return a short confirmation of the six rules updated and their target active states.
```

## Low-Level Option

If you do not want the preset tool, the scheduler can instead call `update_automation_rule` six times directly. That is closer to the raw REST implementation, but the preset tool is safer because:

- the six rule ids live in one place
- day/night intent is explicit
- the prompt is simpler
- there is less room for a scheduler prompt to flip the wrong rule

## Important Limitation

I still could not read the GitLab work item or note threads directly from this environment. The implementation above is based on the details you pasted, which are enough to model the actual switching logic.

## Sources

- [Schedule recurring tasks in Claude Cowork](https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork)
- [Get started with Claude Cowork](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork)
- [Get started with custom connectors using remote MCP](https://support.anthropic.com/en/articles/11175166-getting-started-with-custom-integrations-using-remote-mcp)
- [OpenAI Academy: Automations](https://openai.com/academy/codex-automations/)
