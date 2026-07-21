import os
from openai import OpenAI
import logging
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

class BaseLLM:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("API key is required.")
        self.api_key = api_key
        self.model = model

    def generate_answer(self, prompt: str, system_prompt: str = None) -> str:
        raise NotImplementedError("This method should be implemented by subclasses.")

    def stream_answer(self, prompt: str, system_prompt: str = None) -> Iterator[str]:
        """流式输出文本 token（默认回退为一次性输出）。"""
        yield self.generate_answer(prompt=prompt, system_prompt=system_prompt)

    def generate_answer_multimodal(self, text: str, image_urls: list[str] | None = None, system_prompt: str | None = None) -> str:
        """可选的多模态回答接口，默认回退为纯文本。"""
        return self.generate_answer(prompt=text, system_prompt=system_prompt)

    def stream_answer_multimodal(self, text: str, image_urls: list[str] | None = None, system_prompt: str | None = None) -> Iterator[str]:
        """流式输出多模态 token（默认回退为一次性输出）。"""
        yield self.generate_answer_multimodal(text=text, image_urls=image_urls, system_prompt=system_prompt)


class GenericOpenAILLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)

        # 本地 vLLM 模式：设置 LLM_BASE_URL 环境变量启用（如 http://localhost:28000/v1）
        # 远程 DashScope 模式：不设置 LLM_BASE_URL，默认走阿里百炼 API
        base_url = os.environ.get("LLM_BASE_URL", "")
        self._is_local = bool(base_url)

        if self._is_local:
            self.client = OpenAI(
                api_key=os.environ.get("DASHSCOPE_API_KEY", "vllm"),
                base_url=base_url,
            )
            self.model = model or "/app/model"
            self.enable_thinking = str(os.environ.get("LLM_ENABLE_THINKING", "true")).lower() == "true"
            self.standard_params = {
                "temperature": 0.6 if self.enable_thinking else 0.7,
                "top_p": 0.95 if self.enable_thinking else 0.8,
            }
            self.extra_backend_params = {
                "top_k": 20,
                "presence_penalty": 1.5,
                "chat_template_kwargs": {
                    "enable_thinking": self.enable_thinking
                }
            }
        else:
            # DashScope 远程 API（默认）
            self.client = OpenAI(
                api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            self.model = model or "qwen-max"
            self.standard_params = {
                "temperature": 0.1,
                "top_p": 0.8,
            }
            self.extra_backend_params = {}

    def generate_answer(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                extra_body=self.extra_backend_params,
                **self.standard_params
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            raise

    def stream_answer(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> Iterator[str]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            stream_iter = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                extra_body=self.extra_backend_params,
                **self.standard_params
            )
            for chunk in stream_iter:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, 'content', None) or (delta.get('content') if isinstance(delta, dict) else None)
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Error streaming LLM API: {e}")
            # 回退：一次性输出
            yield self.generate_answer(prompt, system_prompt=system_prompt)

    def generate_answer_multimodal(self, text: str, image_urls: list[str] | None = None, system_prompt: str | None = None) -> str:
        """多模态图文消息（OpenAI兼容接口）。"""
        system_prompt = system_prompt or "You are a helpful assistant."
        user_content: list[dict] = []
        if image_urls:
            for url in image_urls:
                if not url:
                    continue
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
        user_content.append({"type": "text", "text": text})

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                extra_body=self.extra_backend_params,
                **self.standard_params
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling LLM API (multimodal): {e}")
            raise

    def stream_answer_multimodal(self, text: str, image_urls: list[str] | None = None, system_prompt: str | None = None) -> Iterator[str]:
        """多模态图文消息（OpenAI兼容接口，流式）。"""
        system_prompt = system_prompt or "You are a helpful assistant."
        user_content: list[dict] = []
        if image_urls:
            for url in image_urls:
                if not url:
                    continue
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
        user_content.append({"type": "text", "text": text})

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        try:
            stream_iter = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                extra_body=self.extra_backend_params,
                **self.standard_params
            )
            for chunk in stream_iter:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, 'content', None) or (delta.get('content') if isinstance(delta, dict) else None)
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Error calling LLM API (multimodal/stream): {e}")
            # 回退：一次性输出
            yield self.generate_answer_multimodal(text, image_urls=image_urls, system_prompt=system_prompt)


def get_llm_service(api_key: str, model_name: str = "qwen-max"):
    """Factory function to get an LLM service instance.
    
    - 未设置 LLM_BASE_URL：走 DashScope 远程 API，model_name 默认 qwen-max
    - 设置了 LLM_BASE_URL：走本地 vLLM 部署，model_name 默认 /app/model
    """
    return GenericOpenAILLM(api_key=api_key, model=model_name)

