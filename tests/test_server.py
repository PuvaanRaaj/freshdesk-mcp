import unittest
from unittest.mock import AsyncMock, patch

from freshdesk_mcp import server


class GetTicketContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_ticket_context_fetches_related_resources(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            side_effect=[
                {"id": 42, "requester_id": 7, "company_id": 9},
                {"body": "summary"},
                [{"id": 1, "body": "conversation"}],
                {"id": 7, "name": "Requester"},
                {"id": 9, "name": "Company"},
            ]
        )

        with patch.object(server, "_client", return_value=mock_client):
            result = await server.get_ticket_context(ticket_id=42)

        self.assertEqual(result["ticket"]["id"], 42)
        self.assertEqual(result["summary"]["body"], "summary")
        self.assertEqual(result["conversations"][0]["id"], 1)
        self.assertEqual(result["requester"]["id"], 7)
        self.assertEqual(result["company"]["id"], 9)

    async def test_get_ticket_context_skips_missing_optional_ids(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[{"id": 42}])

        with patch.object(server, "_client", return_value=mock_client):
            result = await server.get_ticket_context(
                ticket_id=42,
                include_summary=False,
                include_conversations=False,
                include_requester=True,
                include_company=True,
            )

        self.assertEqual(result, {"ticket": {"id": 42}})
        self.assertEqual(mock_client.request.await_count, 1)

    async def test_get_optional_resource_returns_none_on_runtime_error(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=RuntimeError("boom"))

        with patch.object(server, "_client", return_value=mock_client):
            result = await server._get_optional_resource("tickets/42/summary")

        self.assertIsNone(result)


class AutomationRuleTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_automation_rule_calls_expected_endpoint(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"id": 51001008328, "active": True})

        with patch.object(server, "_client", return_value=mock_client):
            result = await server.update_automation_rule(
                automation_type=1,
                rule_id=51001008328,
                active=True,
            )

        self.assertEqual(result["active"], True)
        mock_client.request.assert_awaited_once_with(
            "PUT",
            "automations/1/rules/51001008328",
            json={"active": True},
        )

    async def test_switch_assignment_shift_updates_day_rules(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[{"ok": True}] * len(server.DAY_SHIFT_RULES))

        with patch.object(server, "_client", return_value=mock_client):
            result = await server.switch_assignment_shift("day")

        self.assertEqual(result["shift"], "day")
        self.assertEqual(len(result["updated_rules"]), len(server.DAY_SHIFT_RULES))
        calls = mock_client.request.await_args_list
        self.assertEqual(len(calls), len(server.DAY_SHIFT_RULES))
        self.assertEqual(calls[0].args[0], "PUT")
        self.assertEqual(calls[0].args[1], "automations/1/rules/51001008328")
        self.assertEqual(calls[0].kwargs["json"], {"active": True})

    async def test_switch_assignment_shift_rejects_unknown_shift(self) -> None:
        with self.assertRaises(ValueError):
            await server.switch_assignment_shift("swing")


class SearchHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_tickets_by_type_builds_expected_query(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"results": []})

        with patch.object(server, "_client", return_value=mock_client):
            await server.search_tickets_by_type(issue_type="refund", status=2, priority=4, page=2)

        mock_client.request.assert_awaited_once_with(
            "GET",
            "search/tickets",
            params={"query": "type:'refund' AND status:2 AND priority:4", "page": 2},
        )

    async def test_search_tickets_by_tag_builds_expected_query(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"results": []})

        with patch.object(server, "_client", return_value=mock_client):
            await server.search_tickets_by_tag(tag="payment_failed", status=3)

        mock_client.request.assert_awaited_once_with(
            "GET",
            "search/tickets",
            params={"query": "tag:'payment_failed' AND status:3", "page": 1},
        )

    async def test_search_tickets_by_date_range_builds_expected_query(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"results": []})

        with patch.object(server, "_client", return_value=mock_client):
            await server.search_tickets_by_date_range(
                field_name="created_at",
                start_date="2026-04-01",
                end_date="2026-04-30",
                status=2,
            )

        mock_client.request.assert_awaited_once_with(
            "GET",
            "search/tickets",
            params={
                "query": "created_at:>'2026-04-01' AND created_at:<'2026-04-30' AND status:2",
                "page": 1,
            },
        )

    async def test_search_tickets_by_date_range_validates_inputs(self) -> None:
        with self.assertRaises(ValueError):
            await server.search_tickets_by_date_range(field_name="subject")

        with self.assertRaises(ValueError):
            await server.search_tickets_by_date_range(field_name="created_at")

    async def test_find_refund_tickets_builds_expected_query(self) -> None:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"results": []})

        with patch.object(server, "_client", return_value=mock_client):
            await server.find_refund_tickets(status=2, priority=3, page=4)

        mock_client.request.assert_awaited_once_with(
            "GET",
            "search/tickets",
            params={
                "query": "(type:'refund' OR tag:'refund') AND status:2 AND priority:3",
                "page": 4,
            },
        )


if __name__ == "__main__":
    unittest.main()
