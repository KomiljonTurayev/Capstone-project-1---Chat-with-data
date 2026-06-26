import pytest
from unittest.mock import MagicMock, patch
from tools import get_schema, query_database, create_github_issue, dispatch_tool


def test_get_schema_contains_table_names():
    schema = get_schema()
    assert "customers" in schema
    assert "products" in schema
    assert "orders" in schema
    assert "order_items" in schema


def test_get_schema_contains_column_names():
    schema = get_schema()
    assert "email" in schema
    assert "total_amount" in schema
    assert "category" in schema


def test_query_database_returns_results():
    result = query_database("SELECT COUNT(*) as cnt FROM customers")
    assert isinstance(result, str)
    assert len(result) > 0


def test_query_database_blocks_dangerous_sql():
    with pytest.raises(PermissionError):
        query_database("DELETE FROM customers")


def test_query_database_limits_rows():
    result = query_database("SELECT * FROM order_items")
    assert isinstance(result, str)
    lines = [l for l in result.strip().split("\n") if l.strip()]
    assert len(lines) <= 103  # header + separator + 100 rows + possible footer


def test_create_github_issue_returns_url(mocker):
    mock_repo = MagicMock()
    mock_issue = MagicMock()
    mock_issue.html_url = "https://github.com/owner/repo/issues/1"
    mock_repo.create_issue.return_value = mock_issue

    mock_github = mocker.patch("tools.Github")
    mock_github.return_value.get_repo.return_value = mock_repo

    mocker.patch.dict("os.environ", {
        "GITHUB_TOKEN": "fake-token",
        "GITHUB_REPO": "owner/repo",
    })

    url = create_github_issue("Test Issue", "Test body")
    assert url == "https://github.com/owner/repo/issues/1"
    mock_repo.create_issue.assert_called_once_with(title="Test Issue", body="Test body")


def test_dispatch_tool_routes_get_schema():
    result = dispatch_tool("get_schema", {})
    assert "customers" in result


def test_dispatch_tool_routes_query_database():
    result = dispatch_tool("query_database", {"sql": "SELECT COUNT(*) FROM products"})
    assert isinstance(result, str)


def test_dispatch_tool_unknown_tool():
    result = dispatch_tool("nonexistent_tool", {})
    assert "Unknown tool" in result
