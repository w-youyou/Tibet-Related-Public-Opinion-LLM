import pytest
from chunker_api.rag.question_router import QuestionRouter


class TestQuestionRouter:
    def setup_method(self):
        self.router = QuestionRouter()

    def test_greeting_returns_false(self):
        assert not self.router.needs_knowledge_base("你好", "")
        assert not self.router.needs_knowledge_base("谢谢", "")

    def test_policy_keyword_returns_true(self):
        assert self.router.needs_knowledge_base("涉藏舆情监测的方法有哪些？", "")
        assert self.router.needs_knowledge_base("西藏自治区民族政策有哪些？", "")

    def test_out_of_scope_returns_false(self):
        assert not self.router.needs_knowledge_base("今天天气怎么样", "")
        assert not self.router.needs_knowledge_base("给我讲个笑话", "")

    def test_math_returns_false(self):
        assert not self.router.needs_knowledge_base("1+1等于几", "")

    def test_is_out_of_scope(self):
        assert self.router.is_out_of_scope("今天天气怎么样")
        assert self.router.is_out_of_scope("给我讲个笑话")
        assert not self.router.is_out_of_scope("舆情传播路径如何分析？")

    def test_empty_question_returns_false(self):
        assert not self.router.needs_knowledge_base("", "")
        assert not self.router.needs_knowledge_base("   ", "")

    def test_normalize_removes_punctuation_and_spaces(self):
        lower, compact, plain = self.router._normalize("你好！请问，涉藏舆情如何监测？")
        assert "低保" in compact
        assert "你好请问涉藏舆情如何监测" == plain
