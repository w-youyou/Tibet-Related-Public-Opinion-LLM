import pytest
from unittest.mock import Mock, patch, MagicMock
from chunker_api.rag.answer_builder import AnswerBuilder


class MockLLM:
    """Mock LLM for testing AnswerBuilder without real API calls."""

    def __init__(self, answer="mock answer"):
        self.answer = answer
        self.generate_answer_calls = []
        self.stream_answer_calls = []

    def generate_answer(self, prompt, system_prompt=None):
        self.generate_answer_calls.append((prompt, system_prompt))
        return self.answer

    def stream_answer(self, prompt, system_prompt=None):
        self.stream_answer_calls.append((prompt, system_prompt))
        yield "mock stream answer"


class TestAnswerBuilder:
    def setup_method(self):
        self.mock_llm = MockLLM()
        self.builder = AnswerBuilder(self.mock_llm)

    # 1. format_history empty -> ""
    def test_format_history_empty(self):
        assert self.builder.format_history(None) == ""
        assert self.builder.format_history([]) == ""

    # 2. format_history with messages -> correct formatting
    def test_format_history_with_messages(self):
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮助你的？"},
        ]
        result = self.builder.format_history(history)
        assert "对话历史:" in result
        assert "用户:你好" in result
        assert "助手:你好，有什么可以帮助你的？" in result
        assert result.endswith("\n\n")

    # 3. generate_title truncation
    def test_generate_title_truncation(self):
        long_answer = "a" * 60
        mock_title_llm = MockLLM(answer=long_answer)
        with patch('chunker_api.rag.answer_builder.get_llm_service', return_value=mock_title_llm):
            title = self.builder.generate_title("test question", "test answer", api_key="fake-key")
            assert len(title) <= 50

    # 4. generate_title strips quotes
    def test_generate_title_strips_quotes(self):
        mock_title_llm = MockLLM(answer='"My Title"')
        with patch('chunker_api.rag.answer_builder.get_llm_service', return_value=mock_title_llm):
            title = self.builder.generate_title("test question", "test answer", api_key="fake-key")
            assert '"' not in title
            assert title == "My Title"

    # 5. generate_suggested_next_questions returns list
    def test_generate_suggested_next_questions_returns_list(self):
        self.mock_llm.answer = "如何准备申请材料\n办理需要多长时间\n可以在哪里办理"
        questions = self.builder.generate_suggested_next_questions(
            "如何申请低保", "您可以前往社区服务中心提交申请材料。"
        )
        assert isinstance(questions, list)
        assert len(questions) >= 1
        assert all(isinstance(q, str) for q in questions)

    # 6. generate delegates to llm.generate_answer
    def test_generate_delegates_to_llm(self):
        result = self.builder.generate("system prompt", "user prompt")
        assert result == "mock answer"
        assert len(self.mock_llm.generate_answer_calls) == 1
        assert self.mock_llm.generate_answer_calls[0][0] == "user prompt"
        assert self.mock_llm.generate_answer_calls[0][1] == "system prompt"
