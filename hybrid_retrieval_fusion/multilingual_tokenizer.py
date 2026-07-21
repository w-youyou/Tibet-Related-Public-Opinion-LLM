# -*- coding: utf-8 -*-
"""
MultilingualTokenizer — 多语言分词器。

支持中文（jieba）、藏文（基于 tsheg 分词）、英文（空格分词）的混合文本。
自动检测文本中的语言成分并分别处理。
"""

import re
import jieba
from typing import List


# 藏文 Unicode 范围: U+0F00 - U+0FFF
# tsheg (་) 是藏文词分隔符, U+0F0B
# tibetan vowel signs: U+0F71-U+0F7D
# tibetan consonants: U+0F40-U+0F6C
_TIBETAN_RANGE = re.compile(r'[\u0F00-\u0FFF]')
_CJK_RANGE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
_LATIN_RANGE = re.compile(r'[a-zA-Z]+')
_TSEG = '\u0F0B'  # 藏文词分隔符 tsheg
# 藏文标点与特殊符号
_TIBETAN_PUNCT = re.compile(r'[\u0F00-\u0F0F\u0F10-\u0F1A\u0F3A-\u0F3D\u0F85]')


def _detect_segments(text: str) -> List[tuple]:
    """将混合文本切分为 (segment_text, language) 的列表。
    
    language: 'tibetan' | 'chinese' | 'latin' | 'other'
    """
    if not text:
        return []
    
    segments = []
    i = 0
    n = len(text)
    
    while i < n:
        ch = text[i]
        
        # 检测藏文
        if _TIBETAN_RANGE.match(ch):
            j = i + 1
            while j < n and (_TIBETAN_RANGE.match(text[j]) or text[j] == _TSEG or text[j].isspace() and j + 1 < n and _TIBETAN_RANGE.match(text[j + 1])):
                j += 1
            segments.append((text[i:j], 'tibetan'))
            i = j
            continue
        
        # 检测 CJK
        if _CJK_RANGE.match(ch):
            j = i + 1
            while j < n and _CJK_RANGE.match(text[j]):
                j += 1
            segments.append((text[i:j], 'chinese'))
            i = j
            continue
        
        # 检测拉丁字母
        if ch.isalpha() and ord(ch) < 0x0F00:
            j = i + 1
            while j < n and text[j].isalpha() and ord(text[j]) < 0x0F00:
                j += 1
            segments.append((text[i:j], 'latin'))
            i = j
            continue
        
        # 数字
        if ch.isdigit():
            j = i + 1
            while j < n and (text[j].isdigit() or text[j] in '.,%'):
                j += 1
            segments.append((text[i:j], 'other'))
            i = j
            continue
        
        # 其他字符（标点、空格等）跳过
        i += 1
    
    return segments


class MultilingualTokenizer:
    """多语言分词器，支持中文/藏文/英文混合文本。
    
    用法:
        tokenizer = MultilingualTokenizer()
        tokens = tokenizer.tokenize("这是中文和བོད་སྐད་ mixed text")
    """
    
    def __init__(self, use_jieba: bool = True):
        self.use_jieba = use_jieba
        self._jieba_initialized = False
    
    def _ensure_jieba(self):
        if self.use_jieba and not self._jieba_initialized:
            jieba.initialize()
            self._jieba_initialized = True
    
    def tokenize_tibetan(self, text: str) -> List[str]:
        """藏文分词：基于 tsheg (་) 分隔符切分。
        
        藏文天然以 tsheg 作为音节/词的分隔标记，
        因此按 tsheg 切分即可得到基本的词单元。
        """
        if not text:
            return []
        # 先去除藏文标点
        text = _TIBETAN_PUNCT.sub(' ', text)
        # 按 tsheg 和空格切分
        parts = re.split(r'[\u0F0B\s]+', text)
        tokens = []
        for p in parts:
            p = p.strip()
            if p and len(p) >= 2:  # 过滤过短的片段
                tokens.append(p)
        return tokens
    
    def tokenize_chinese(self, text: str) -> List[str]:
        """中文分词：使用 jieba。"""
        if not text:
            return []
        self._ensure_jieba()
        return jieba.lcut(text)
    
    def tokenize_latin(self, text: str) -> List[str]:
        """拉丁文分词：按空格切分并转小写。"""
        if not text:
            return []
        return [w.lower() for w in text.split() if w]
    
    def tokenize(self, text: str) -> List[str]:
        """对混合文本进行多语言分词。
        
        自动检测文本中的语言成分，分别使用对应的分词策略，
        最终返回合并后的 token 列表。
        """
        if not text:
            return []
        
        segments = _detect_segments(text)
        tokens = []
        
        for seg_text, lang in segments:
            if lang == 'tibetan':
                tokens.extend(self.tokenize_tibetan(seg_text))
            elif lang == 'chinese':
                tokens.extend(self.tokenize_chinese(seg_text))
            elif lang == 'latin':
                tokens.extend(self.tokenize_latin(seg_text))
            else:
                if seg_text.strip():
                    tokens.append(seg_text.strip())
        
        return tokens
    
    def tokenize_query(self, query: str) -> List[str]:
        """对查询文本进行分词，与 tokenize 相同但可做查询特定的优化。"""
        return self.tokenize(query)