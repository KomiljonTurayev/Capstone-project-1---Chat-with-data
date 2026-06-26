import pytest
from unittest.mock import MagicMock, patch
from agent import log, run_agent


def test_log_prints_formatted_message(capsys):
    log("USER", "hello world")
    captured = capsys.readouterr()
    assert "USER" in captured.out
    assert "hello world" in captured.out


def test_run_agent_returns_string_on_end_turn(mocker):
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Here is your answer."
    mock_response.content = [text_block]

    mock_client = mocker.patch("agent.client")
    mock_client.messages.create.return_value = mock_response

    result = run_agent([{"role": "user", "content": "Hello"}])
    assert result == "Here is your answer."


def test_run_agent_dispatches_tool_and_continues(mocker):
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "get_schema"
    tool_block.id = "tool_123"
    tool_block.input = {}

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "The schema is..."

    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [tool_block]

    end_response = MagicMock()
    end_response.stop_reason = "end_turn"
    end_response.content = [text_block]

    mock_client = mocker.patch("agent.client")
    mock_client.messages.create.side_effect = [tool_response, end_response]

    mock_dispatch = mocker.patch("agent.dispatch_tool", return_value="schema result")

    result = run_agent([{"role": "user", "content": "What tables exist?"}])
    assert result == "The schema is..."
    mock_dispatch.assert_called_once_with("get_schema", {})
