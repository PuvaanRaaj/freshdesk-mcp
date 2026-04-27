from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import FreshdeskClient
from .config import FreshdeskSettings

mcp = FastMCP("freshdesk")


def _client() -> FreshdeskClient:
    return FreshdeskClient(FreshdeskSettings.from_env())


def _payload_with_extra(
    base: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(base)
    if extra:
        payload.update(extra)
    return payload


async def _get_optional_resource(path: str) -> Any | None:
    try:
        return await _client().request("GET", path)
    except RuntimeError:
        return None


def _format_search_value(value: str | int | bool | date) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()

    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _build_search_clause(
    field: str,
    value: str | int | bool | date,
    *,
    operator: str = ":",
) -> str:
    return f"{field}{operator}{_format_search_value(value)}"


def _combine_clauses(clauses: list[str], *, joiner: str = "AND") -> str:
    filtered = [clause for clause in clauses if clause]
    if not filtered:
        raise ValueError("At least one search clause is required.")
    if len(filtered) == 1:
        return filtered[0]
    return f" {joiner} ".join(filtered)


DAY_SHIFT_RULES: tuple[tuple[int, int, bool], ...] = (
    (1, 51001008328, True),
    (1, 51001005307, False),
    (4, 51001020738, False),
    (4, 51000234971, True),
    (4, 51000234972, True),
    (4, 51001017301, False),
)


NIGHT_SHIFT_RULES: tuple[tuple[int, int, bool], ...] = (
    (1, 51001008328, False),
    (1, 51001005307, True),
    (4, 51001020738, True),
    (4, 51000234971, False),
    (4, 51000234972, False),
    (4, 51001017301, True),
)


@mcp.tool()
async def create_ticket(
    subject: str,
    description: str,
    source: int,
    priority: int,
    status: int,
    email: str | None = None,
    requester_id: int | None = None,
    custom_fields: dict[str, Any] | None = None,
    additional_fields: dict[str, Any] | None = None,
) -> Any:
    payload = {
        "subject": subject,
        "description": description,
        "source": source,
        "priority": priority,
        "status": status,
    }
    if email is not None:
        payload["email"] = email
    if requester_id is not None:
        payload["requester_id"] = requester_id
    if custom_fields:
        payload["custom_fields"] = custom_fields
    payload = _payload_with_extra(payload, additional_fields)
    return await _client().request("POST", "tickets", json=payload)


@mcp.tool()
async def update_ticket(ticket_id: int, ticket_fields: dict[str, Any]) -> Any:
    return await _client().request("PUT", f"tickets/{ticket_id}", json=ticket_fields)


@mcp.tool()
async def delete_ticket(ticket_id: int) -> Any:
    return await _client().request("DELETE", f"tickets/{ticket_id}")


@mcp.tool()
async def search_tickets(query: str) -> Any:
    return await _client().request("GET", "search/tickets", params={"query": query})


@mcp.tool()
async def search_tickets_by_type(
    issue_type: str,
    status: int | None = None,
    priority: int | None = None,
    page: int = 1,
) -> Any:
    clauses = [_build_search_clause("type", issue_type)]
    if status is not None:
        clauses.append(_build_search_clause("status", status))
    if priority is not None:
        clauses.append(_build_search_clause("priority", priority))
    query = _combine_clauses(clauses)
    return await _client().request("GET", "search/tickets", params={"query": query, "page": page})


@mcp.tool()
async def search_tickets_by_tag(
    tag: str,
    status: int | None = None,
    priority: int | None = None,
    page: int = 1,
) -> Any:
    clauses = [_build_search_clause("tag", tag)]
    if status is not None:
        clauses.append(_build_search_clause("status", status))
    if priority is not None:
        clauses.append(_build_search_clause("priority", priority))
    query = _combine_clauses(clauses)
    return await _client().request("GET", "search/tickets", params={"query": query, "page": page})


@mcp.tool()
async def search_tickets_by_date_range(
    field_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    status: int | None = None,
    priority: int | None = None,
    page: int = 1,
) -> Any:
    allowed_fields = {"created_at", "updated_at", "due_by", "fr_due_by"}
    if field_name not in allowed_fields:
        raise ValueError(f"field_name must be one of {sorted(allowed_fields)}")
    if start_date is None and end_date is None:
        raise ValueError("At least one of start_date or end_date is required.")

    clauses: list[str] = []
    if start_date is not None:
        clauses.append(_build_search_clause(field_name, start_date, operator=":>"))
    if end_date is not None:
        clauses.append(_build_search_clause(field_name, end_date, operator=":<"))
    if status is not None:
        clauses.append(_build_search_clause("status", status))
    if priority is not None:
        clauses.append(_build_search_clause("priority", priority))
    query = _combine_clauses(clauses)
    return await _client().request("GET", "search/tickets", params={"query": query, "page": page})


@mcp.tool()
async def find_refund_tickets(
    status: int | None = None,
    priority: int | None = None,
    page: int = 1,
) -> Any:
    refund_match = _combine_clauses(
        [
            _build_search_clause("type", "refund"),
            _build_search_clause("tag", "refund"),
        ],
        joiner="OR",
    )
    clauses = [f"({refund_match})"]
    if status is not None:
        clauses.append(_build_search_clause("status", status))
    if priority is not None:
        clauses.append(_build_search_clause("priority", priority))
    query = _combine_clauses(clauses)
    return await _client().request("GET", "search/tickets", params={"query": query, "page": page})


@mcp.tool()
async def get_ticket_fields() -> Any:
    return await _client().request("GET", "ticket_fields")


@mcp.tool()
async def get_tickets(page: int = 1, per_page: int = 30) -> Any:
    return await _client().request("GET", "tickets", params={"page": page, "per_page": per_page})


@mcp.tool()
async def get_ticket(ticket_id: int) -> Any:
    return await _client().request("GET", f"tickets/{ticket_id}")


@mcp.tool()
async def get_automation_rule(automation_type: int, rule_id: int) -> Any:
    return await _client().request("GET", f"automations/{automation_type}/rules/{rule_id}")


@mcp.tool()
async def update_automation_rule(automation_type: int, rule_id: int, active: bool) -> Any:
    return await _client().request(
        "PUT",
        f"automations/{automation_type}/rules/{rule_id}",
        json={"active": active},
    )


@mcp.tool()
async def switch_assignment_shift(shift: str) -> Any:
    normalized_shift = shift.strip().lower()
    if normalized_shift not in {"day", "night"}:
        raise ValueError("shift must be 'day' or 'night'.")

    rule_updates = DAY_SHIFT_RULES if normalized_shift == "day" else NIGHT_SHIFT_RULES
    results = await asyncio.gather(
        *(
            _client().request(
                "PUT",
                f"automations/{automation_type}/rules/{rule_id}",
                json={"active": active},
            )
            for automation_type, rule_id, active in rule_updates
        )
    )

    return {
        "shift": normalized_shift,
        "updated_rules": [
            {
                "automation_type": automation_type,
                "rule_id": rule_id,
                "active": active,
                "result": result,
            }
            for (automation_type, rule_id, active), result in zip(rule_updates, results)
        ],
    }


@mcp.tool()
async def get_ticket_context(
    ticket_id: int,
    include_summary: bool = True,
    include_conversations: bool = True,
    include_requester: bool = True,
    include_company: bool = True,
) -> Any:
    ticket = await _client().request("GET", f"tickets/{ticket_id}")
    if not isinstance(ticket, dict):
        return {"ticket": ticket}

    result: dict[str, Any] = {"ticket": ticket}
    follow_up_tasks: list[tuple[str, Any]] = []

    if include_summary:
        follow_up_tasks.append(("summary", _get_optional_resource(f"tickets/{ticket_id}/summary")))
    if include_conversations:
        follow_up_tasks.append(("conversations", _get_optional_resource(f"tickets/{ticket_id}/conversations")))

    requester_id = ticket.get("requester_id")
    if include_requester and isinstance(requester_id, int):
        follow_up_tasks.append(("requester", _get_optional_resource(f"contacts/{requester_id}")))

    company_id = ticket.get("company_id")
    if include_company and isinstance(company_id, int):
        follow_up_tasks.append(("company", _get_optional_resource(f"companies/{company_id}")))

    if not follow_up_tasks:
        return result

    values = await asyncio.gather(*(task for _, task in follow_up_tasks))
    for (name, _), value in zip(follow_up_tasks, values):
        result[name] = value
    return result


@mcp.tool()
async def get_ticket_conversation(ticket_id: int) -> Any:
    return await _client().request("GET", f"tickets/{ticket_id}/conversations")


@mcp.tool()
async def create_ticket_reply(ticket_id: int, body: str) -> Any:
    return await _client().request("POST", f"tickets/{ticket_id}/reply", json={"body": body})


@mcp.tool()
async def create_ticket_note(ticket_id: int, body: str, private: bool = False) -> Any:
    return await _client().request(
        "POST",
        f"tickets/{ticket_id}/notes",
        json={"body": body, "private": private},
    )


@mcp.tool()
async def update_ticket_conversation(conversation_id: int, body: str) -> Any:
    return await _client().request(
        "PUT",
        f"conversations/{conversation_id}",
        json={"body": body},
    )


@mcp.tool()
async def view_ticket_summary(ticket_id: int) -> Any:
    return await _client().request("GET", f"tickets/{ticket_id}/summary")


@mcp.tool()
async def update_ticket_summary(ticket_id: int, body: str) -> Any:
    return await _client().request("PUT", f"tickets/{ticket_id}/summary", json={"body": body})


@mcp.tool()
async def delete_ticket_summary(ticket_id: int) -> Any:
    return await _client().request("DELETE", f"tickets/{ticket_id}/summary")


@mcp.tool()
async def get_agents(page: int = 1, per_page: int = 30) -> Any:
    return await _client().request("GET", "agents", params={"page": page, "per_page": per_page})


@mcp.tool()
async def view_agent(agent_id: int) -> Any:
    return await _client().request("GET", f"agents/{agent_id}")


@mcp.tool()
async def create_agent(agent_fields: dict[str, Any]) -> Any:
    return await _client().request("POST", "agents", json=agent_fields)


@mcp.tool()
async def update_agent(agent_id: int, agent_fields: dict[str, Any]) -> Any:
    return await _client().request("PUT", f"agents/{agent_id}", json=agent_fields)


@mcp.tool()
async def search_agents(query: str) -> Any:
    return await _client().request("GET", "search/agents", params={"query": query})


@mcp.tool()
async def list_contacts(page: int = 1, per_page: int = 30) -> Any:
    return await _client().request("GET", "contacts", params={"page": page, "per_page": per_page})


@mcp.tool()
async def get_contact(contact_id: int) -> Any:
    return await _client().request("GET", f"contacts/{contact_id}")


@mcp.tool()
async def search_contacts(query: str) -> Any:
    return await _client().request("GET", "search/contacts", params={"query": query})


@mcp.tool()
async def update_contact(contact_id: int, contact_fields: dict[str, Any]) -> Any:
    return await _client().request("PUT", f"contacts/{contact_id}", json=contact_fields)


@mcp.tool()
async def list_companies(page: int = 1, per_page: int = 30) -> Any:
    return await _client().request("GET", "companies", params={"page": page, "per_page": per_page})


@mcp.tool()
async def view_company(company_id: int) -> Any:
    return await _client().request("GET", f"companies/{company_id}")


@mcp.tool()
async def search_companies(query: str) -> Any:
    return await _client().request("GET", "search/companies", params={"query": query})


@mcp.tool()
async def find_company_by_name(name: str) -> Any:
    results = await _client().request("GET", "search/companies", params={"query": f"name:'{name}'"})
    if not isinstance(results, dict):
        return results

    companies = results.get("results", [])
    exact_matches = [
        company
        for company in companies
        if isinstance(company, dict) and str(company.get("name", "")).casefold() == name.casefold()
    ]
    return {
        "query": name,
        "matches": exact_matches or companies,
    }


@mcp.tool()
async def list_company_fields() -> Any:
    return await _client().request("GET", "company_fields")


def main() -> None:
    mcp.run()
