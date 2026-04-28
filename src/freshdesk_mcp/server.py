from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import FreshdeskClient
from .config import FreshdeskSettings

mcp = FastMCP("freshdesk")
MALAYSIA_TZ = timezone(timedelta(hours=8))
DATETIME_FIELDS = {
    "created_at",
    "updated_at",
    "due_by",
    "fr_due_by",
    "closed_at",
    "next_response_due_by",
    "next_action_due_by",
}


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


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalize_datetime_fields(value: Any, parent_key: str | None = None) -> Any:
    if isinstance(value, list):
        return [_normalize_datetime_fields(item) for item in value]

    if isinstance(value, dict):
        return {key: _normalize_datetime_fields(item, key) for key, item in value.items()}

    if isinstance(value, str) and parent_key in DATETIME_FIELDS:
        try:
            dt = _parse_datetime(value)
        except ValueError:
            return value
        return dt.astimezone(MALAYSIA_TZ).isoformat()

    return value


def _ticket_search_text(ticket: dict[str, Any]) -> str:
    parts: list[str] = []

    for field_name in ("subject", "description_text", "description"):
        value = ticket.get(field_name)
        if isinstance(value, str) and value:
            parts.append(value)

    for tag in ticket.get("tags") or []:
        if isinstance(tag, str) and tag:
            parts.append(tag)

    custom_fields = ticket.get("custom_fields") or {}
    if isinstance(custom_fields, dict):
        for value in custom_fields.values():
            if isinstance(value, str) and value:
                parts.append(value)

    return " ".join(parts).casefold()


def _agent_match_text(agent: dict[str, Any]) -> str:
    parts: list[str] = []

    for field_name in ("contact", "name", "email", "occasional"):
        value = agent.get(field_name)
        if isinstance(value, str) and value:
            parts.append(value)

    contact = agent.get("contact")
    if isinstance(contact, dict):
        for field_name in ("name", "email"):
            value = contact.get(field_name)
            if isinstance(value, str) and value:
                parts.append(value)

    return " ".join(parts).casefold()


def _select_agent_match(agents: list[dict[str, Any]], agent_identifier: str) -> dict[str, Any] | None:
    normalized = agent_identifier.strip().casefold()
    if not normalized:
        return None

    exact_matches: list[dict[str, Any]] = []
    partial_matches: list[dict[str, Any]] = []

    for agent in agents:
        haystack = _agent_match_text(agent)
        if not haystack:
            continue
        if normalized == haystack or any(part.casefold() == normalized for part in haystack.split()):
            exact_matches.append(agent)
        elif normalized in haystack:
            partial_matches.append(agent)

    return exact_matches[0] if exact_matches else partial_matches[0] if partial_matches else None


def _ticket_url(ticket_id: int) -> str:
    return f"{FreshdeskSettings.from_env().base_url}/helpdesk/tickets/{ticket_id}"


def _enrich_ticket(ticket: Any) -> Any:
    if isinstance(ticket, dict) and isinstance(ticket.get("id"), int):
        ticket["url"] = _ticket_url(ticket["id"])
    return ticket


def _enrich_tickets_response(response: Any) -> Any:
    if isinstance(response, list):
        return [_enrich_ticket(t) for t in response]
    if isinstance(response, dict):
        if "results" in response:
            response["results"] = [_enrich_ticket(t) for t in response.get("results", [])]
        else:
            _enrich_ticket(response)
    return response


def _finalize_response(response: Any) -> Any:
    return _enrich_tickets_response(_normalize_datetime_fields(response))


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
    return _finalize_response(await _client().request("POST", "tickets", json=payload))


@mcp.tool()
async def update_ticket(ticket_id: int, ticket_fields: dict[str, Any]) -> Any:
    return _finalize_response(await _client().request("PUT", f"tickets/{ticket_id}", json=ticket_fields))


@mcp.tool()
async def delete_ticket(ticket_id: int) -> Any:
    return _finalize_response(await _client().request("DELETE", f"tickets/{ticket_id}"))


@mcp.tool()
async def search_tickets(query: str) -> Any:
    return _finalize_response(await _client().request("GET", "search/tickets", params={"query": query}))


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
    return _finalize_response(await _client().request("GET", "search/tickets", params={"query": query, "page": page}))


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
    return _finalize_response(await _client().request("GET", "search/tickets", params={"query": query, "page": page}))


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
    return _finalize_response(await _client().request("GET", "search/tickets", params={"query": query, "page": page}))


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
    return _finalize_response(await _client().request("GET", "search/tickets", params={"query": query, "page": page}))


@mcp.tool()
async def find_tickets_by_keywords(
    keywords: list[str],
    start_at: str,
    end_at: str | None = None,
    time_field: str = "created_at",
    match_all: bool = False,
    status: int | None = None,
    priority: int | None = None,
    page_limit: int = 10,
    per_page: int = 100,
) -> Any:
    if not keywords:
        raise ValueError("keywords must contain at least one entry.")
    if time_field not in {"created_at", "updated_at"}:
        raise ValueError("time_field must be 'created_at' or 'updated_at'.")
    if page_limit < 1:
        raise ValueError("page_limit must be at least 1.")
    if per_page < 1 or per_page > 100:
        raise ValueError("per_page must be between 1 and 100.")

    start_dt = _parse_datetime(start_at)
    end_dt = _parse_datetime(end_at) if end_at is not None else None
    normalized_keywords = [keyword.strip().casefold() for keyword in keywords if keyword.strip()]
    if not normalized_keywords:
        raise ValueError("keywords must contain at least one non-empty value.")

    matched_tickets: list[dict[str, Any]] = []
    scanned_count = 0
    page = 1

    fetch_since = start_dt.isoformat() if time_field == "updated_at" else None

    while page <= page_limit:
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if fetch_since is not None:
            params["updated_since"] = fetch_since

        batch = await _client().request("GET", "tickets", params=params)
        if not isinstance(batch, list) or not batch:
            break

        scanned_count += len(batch)

        for raw_ticket in batch:
            if not isinstance(raw_ticket, dict):
                continue

            ticket_time_raw = raw_ticket.get(time_field)
            if not isinstance(ticket_time_raw, str):
                continue

            ticket_dt = _parse_datetime(ticket_time_raw)
            if ticket_dt < start_dt:
                continue
            if end_dt is not None and ticket_dt > end_dt:
                continue
            if status is not None and raw_ticket.get("status") != status:
                continue
            if priority is not None and raw_ticket.get("priority") != priority:
                continue

            haystack = _ticket_search_text(raw_ticket)
            matched = all(keyword in haystack for keyword in normalized_keywords) if match_all else any(
                keyword in haystack for keyword in normalized_keywords
            )
            if matched:
                matched_tickets.append(_finalize_response(raw_ticket))

        if len(batch) < per_page:
            break
        page += 1

    matched_tickets.sort(key=lambda ticket: ticket.get(time_field, ""), reverse=True)
    return _finalize_response({
        "keywords": keywords,
        "time_field": time_field,
        "start_at": start_at,
        "end_at": end_at,
        "match_all": match_all,
        "status": status,
        "priority": priority,
        "scanned_count": scanned_count,
        "match_count": len(matched_tickets),
        "tickets": matched_tickets,
    })


@mcp.tool()
async def get_tickets_assigned_to_agent(
    agent_id: int,
    status: int | None = None,
    priority: int | None = None,
    page: int = 1,
) -> Any:
    clauses = [_build_search_clause("responder_id", agent_id)]
    if status is not None:
        clauses.append(_build_search_clause("status", status))
    if priority is not None:
        clauses.append(_build_search_clause("priority", priority))
    query = _combine_clauses(clauses)
    response = _finalize_response(await _client().request("GET", "search/tickets", params={"query": query, "page": page}))
    if isinstance(response, dict):
        response["agent_id"] = agent_id
    return response


@mcp.tool()
async def get_tickets_assigned_to_agent_identifier(
    agent_identifier: str,
    status: int | None = None,
    priority: int | None = None,
    page: int = 1,
) -> Any:
    agent_results = _finalize_response(await _client().request("GET", "search/agents", params={"query": agent_identifier}))
    if not isinstance(agent_results, dict):
        return _finalize_response(
            {"agent_identifier": agent_identifier, "matched_agent": None, "tickets": [], "raw_agents": agent_results}
        )

    agents = agent_results.get("results", [])
    if not isinstance(agents, list):
        agents = []

    matched_agent = _select_agent_match(
        [agent for agent in agents if isinstance(agent, dict)],
        agent_identifier,
    )

    if matched_agent is None:
        return _finalize_response({
            "agent_identifier": agent_identifier,
            "matched_agent": None,
            "candidate_agents": agents,
            "tickets": [],
        })

    agent_id = matched_agent.get("id")
    if not isinstance(agent_id, int):
        return _finalize_response({
            "agent_identifier": agent_identifier,
            "matched_agent": matched_agent,
            "tickets": [],
        })

    ticket_results = await get_tickets_assigned_to_agent(
        agent_id=agent_id,
        status=status,
        priority=priority,
        page=page,
    )
    if isinstance(ticket_results, dict):
        ticket_results["agent_identifier"] = agent_identifier
        ticket_results["matched_agent"] = matched_agent
    return _finalize_response(ticket_results)


@mcp.tool()
async def get_ticket_fields() -> Any:
    return _finalize_response(await _client().request("GET", "ticket_fields"))


@mcp.tool()
async def get_tickets(page: int = 1, per_page: int = 30) -> Any:
    return _finalize_response(await _client().request("GET", "tickets", params={"page": page, "per_page": per_page}))


@mcp.tool()
async def get_ticket(ticket_id: int) -> Any:
    return _finalize_response(await _client().request("GET", f"tickets/{ticket_id}"))


@mcp.tool()
async def get_automation_rule(automation_type: int, rule_id: int) -> Any:
    return _finalize_response(await _client().request("GET", f"automations/{automation_type}/rules/{rule_id}"))


@mcp.tool()
async def update_automation_rule(automation_type: int, rule_id: int, active: bool) -> Any:
    return _finalize_response(
        await _client().request(
        "PUT",
        f"automations/{automation_type}/rules/{rule_id}",
        json={"active": active},
    ))


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

    return _finalize_response({
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
    })


@mcp.tool()
async def get_ticket_context(
    ticket_id: int,
    include_summary: bool = True,
    include_conversations: bool = True,
    include_requester: bool = True,
    include_company: bool = True,
) -> Any:
    ticket = _finalize_response(await _client().request("GET", f"tickets/{ticket_id}"))
    if not isinstance(ticket, dict):
        return _finalize_response({"ticket": ticket})

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
        return _finalize_response(result)

    values = await asyncio.gather(*(task for _, task in follow_up_tasks))
    for (name, _), value in zip(follow_up_tasks, values):
        result[name] = _finalize_response(value)
    return _finalize_response(result)


@mcp.tool()
async def get_ticket_conversation(ticket_id: int) -> Any:
    return _finalize_response(await _client().request("GET", f"tickets/{ticket_id}/conversations"))


@mcp.tool()
async def create_ticket_reply(ticket_id: int, body: str) -> Any:
    return _finalize_response(await _client().request("POST", f"tickets/{ticket_id}/reply", json={"body": body}))


@mcp.tool()
async def create_ticket_note(ticket_id: int, body: str, private: bool = False) -> Any:
    return _finalize_response(await _client().request(
        "POST",
        f"tickets/{ticket_id}/notes",
        json={"body": body, "private": private},
    ))


@mcp.tool()
async def update_ticket_conversation(conversation_id: int, body: str) -> Any:
    return _finalize_response(await _client().request(
        "PUT",
        f"conversations/{conversation_id}",
        json={"body": body},
    ))


@mcp.tool()
async def view_ticket_summary(ticket_id: int) -> Any:
    return _finalize_response(await _client().request("GET", f"tickets/{ticket_id}/summary"))


@mcp.tool()
async def update_ticket_summary(ticket_id: int, body: str) -> Any:
    return _finalize_response(await _client().request("PUT", f"tickets/{ticket_id}/summary", json={"body": body}))


@mcp.tool()
async def delete_ticket_summary(ticket_id: int) -> Any:
    return _finalize_response(await _client().request("DELETE", f"tickets/{ticket_id}/summary"))


@mcp.tool()
async def get_agents(page: int = 1, per_page: int = 30) -> Any:
    return _finalize_response(await _client().request("GET", "agents", params={"page": page, "per_page": per_page}))


@mcp.tool()
async def view_agent(agent_id: int) -> Any:
    return _finalize_response(await _client().request("GET", f"agents/{agent_id}"))


@mcp.tool()
async def create_agent(agent_fields: dict[str, Any]) -> Any:
    return _finalize_response(await _client().request("POST", "agents", json=agent_fields))


@mcp.tool()
async def update_agent(agent_id: int, agent_fields: dict[str, Any]) -> Any:
    return _finalize_response(await _client().request("PUT", f"agents/{agent_id}", json=agent_fields))


@mcp.tool()
async def search_agents(query: str) -> Any:
    return _finalize_response(await _client().request("GET", "search/agents", params={"query": query}))


@mcp.tool()
async def list_contacts(page: int = 1, per_page: int = 30) -> Any:
    return _finalize_response(await _client().request("GET", "contacts", params={"page": page, "per_page": per_page}))


@mcp.tool()
async def get_contact(contact_id: int) -> Any:
    return _finalize_response(await _client().request("GET", f"contacts/{contact_id}"))


@mcp.tool()
async def search_contacts(query: str) -> Any:
    return _finalize_response(await _client().request("GET", "search/contacts", params={"query": query}))


@mcp.tool()
async def update_contact(contact_id: int, contact_fields: dict[str, Any]) -> Any:
    return _finalize_response(await _client().request("PUT", f"contacts/{contact_id}", json=contact_fields))


@mcp.tool()
async def list_companies(page: int = 1, per_page: int = 30) -> Any:
    return _finalize_response(await _client().request("GET", "companies", params={"page": page, "per_page": per_page}))


@mcp.tool()
async def view_company(company_id: int) -> Any:
    return _finalize_response(await _client().request("GET", f"companies/{company_id}"))


@mcp.tool()
async def search_companies(query: str) -> Any:
    return _finalize_response(await _client().request("GET", "search/companies", params={"query": query}))


@mcp.tool()
async def find_company_by_name(name: str) -> Any:
    results = _finalize_response(await _client().request("GET", "search/companies", params={"query": f"name:'{name}'"}))
    if not isinstance(results, dict):
        return results

    companies = results.get("results", [])
    exact_matches = [
        company
        for company in companies
        if isinstance(company, dict) and str(company.get("name", "")).casefold() == name.casefold()
    ]
    return _finalize_response({
        "query": name,
        "matches": exact_matches or companies,
    })


@mcp.tool()
async def list_company_fields() -> Any:
    return _finalize_response(await _client().request("GET", "company_fields"))


def main() -> None:
    mcp.run()
