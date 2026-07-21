import re
import math
import os
import json
from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Callable
try:
    from docx import Document  # python-docx
except Exception:  # 延迟导入错误到使用时提示
    Document = None  # type: ignore


def sentence_tokenize(text: str) -> List[str]:
    """将原始纯文本切分为句子，适用于中英文混排等场景。

    - 支持英文标点 (.?!;:) 与常见中文标点（。！？；：）
    - 将连续空行视为潜在段落分隔
    - 尽可能保留句末标点
    """
    if not text:
        return []

    # 归一化换行符
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')

    # 使用带捕获组的正则分隔，使得分隔符（标点）可被保留
    # 包含省略号（... 与 …）、中英文句末标点，并将两个及以上连续换行作为硬分隔
    sep_pattern = r"(\.{3}|…|[\.\!\?\;\:。！？；：])|\n{2,}"
    parts = re.split(sep_pattern, normalized)

    sentences: List[str] = []
    current = []
    for part in parts:
        if part is None:
            continue
        if re.fullmatch(sep_pattern, part or ""):
            # 命中边界；若为标点则附加到当前句末
            if part and part != "\n":
                current.append(part)
            candidate = "".join(current).strip()
            if candidate:
                sentences.append(candidate)
            current = []
        else:
            if part:
                current.append(part)

    # 处理尾部未提交的残留
    tail = "".join(current).strip()
    if tail:
        sentences.append(tail)

    # 后处理：将极短的尾随“句子”并入前句，避免碎片
    merged: List[str] = []
    for sent in sentences:
        if merged and len(sent) < 4:
            merged[-1] = (merged[-1] + (" " if merged[-1] and not merged[-1].endswith("\n") else "") + sent).strip()
        else:
            merged.append(sent)
    return merged


_word_re = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", re.UNICODE)


def tokenize(text: str) -> List[str]:
    """将文本切分为“词/符号”序列。

    - 英文：将字母数字与下划线的连续串作为一个词，并转换为小写
    - 中文：将汉字按单字切分（近似分词）
    """
    tokens: List[str] = []
    for m in _word_re.finditer(text):
        w = m.group(0)
        if len(w) == 1 and ord(w) >= 0x4e00 and ord(w) <= 0x9fff:
            tokens.append(w)  # single CJK char
        else:
            tokens.append(w.lower())
    return tokens


def build_vocabulary(sentences: List[str], tokenizer: Callable[[str], List[str]]) -> Tuple[Dict[str, int], List[List[str]]]:
    tokenized: List[List[str]] = [tokenizer(s) for s in sentences]
    vocab: Dict[str, int] = {}
    for toks in tokenized:
        for t in toks:
            if t not in vocab:
                vocab[t] = len(vocab)
    return vocab, tokenized


def compute_tfidf(tokenized_sentences: List[List[str]], vocabulary: Dict[str, int]) -> List[Dict[int, float]]:
    """为每个句子计算稀疏 TF-IDF 向量（字典：term_index -> 权重）。"""
    num_docs = len(tokenized_sentences)
    if num_docs == 0:
        return []

    # 文档频次（DF）
    doc_freq: defaultdict[int, int] = defaultdict(int)
    for toks in tokenized_sentences:
        unique_terms = set(toks)
        for t in unique_terms:
            doc_freq[vocabulary[t]] += 1

    # 带平滑的 IDF
    idf: Dict[int, float] = {}
    for term_index, df in doc_freq.items():
        idf[term_index] = math.log((1 + num_docs) / (1 + df)) + 1.0

    # 计算 TF 并得到 TF-IDF
    tfidf_vectors: List[Dict[int, float]] = []
    for toks in tokenized_sentences:
        counts = Counter(vocabulary[t] for t in toks)
        max_tf = max(counts.values()) if counts else 1
        vec: Dict[int, float] = {}
        for term_index, tf in counts.items():
            tf_norm = 0.5 + 0.5 * (tf / max_tf)
            vec[term_index] = tf_norm * idf.get(term_index, 0.0)
        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        for k in list(vec.keys()):
            vec[k] /= norm
        tfidf_vectors.append(vec)
    return tfidf_vectors


def cosine_sparse(a: Dict[int, float], b: Dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    # 迭代较小字典以加速
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def block_vector(tfidf_vectors: List[Dict[int, float]], start: int, end: int) -> Dict[int, float]:
    agg: Dict[int, float] = defaultdict(float)
    for i in range(start, end):
        if i < 0 or i >= len(tfidf_vectors):
            continue
        for k, v in tfidf_vectors[i].items():
            agg[k] += v
    # 向量归一化
    norm = math.sqrt(sum(v * v for v in agg.values())) or 1.0
    for k in list(agg.keys()):
        agg[k] /= norm
    return dict(agg)


def texttiling_boundaries(
    sentences: List[str],
    tfidf_vectors: List[Dict[int, float]],
    window_size: int = 6,
    smoothing_width: int = 2,
) -> List[int]:
    """使用类似 TextTiling 的“深度得分”方法检测语义边界。

    返回的是“间隙”索引列表 i，表示在句子 i 与 i+1 之间切分。
    """
    n = len(sentences)
    if n <= 1:
        return []

    # 计算每个间隙两侧语义块的相似度
    sim: List[float] = []
    for gap in range(n - 1):
        left = block_vector(tfidf_vectors, gap - window_size + 1, gap + 1)
        right = block_vector(tfidf_vectors, gap + 1, gap + 1 + window_size)
        sim.append(cosine_sparse(left, right))

    if not sim:
        return []

    # 使用滑动平均平滑相似度曲线
    if smoothing_width > 0:
        smoothed: List[float] = []
        for i in range(len(sim)):
            a = max(0, i - smoothing_width)
            b = min(len(sim), i + smoothing_width + 1)
            smoothed.append(sum(sim[a:b]) / (b - a))
        sim = smoothed

    # “深度”得分：当前位置到左右峰值的落差之和（识别谷底）
    depths: List[float] = [0.0] * len(sim)
    for i in range(1, len(sim) - 1):
        left_peak = max(sim[: i + 1]) if i > 0 else sim[i]
        right_peak = max(sim[i:]) if i < len(sim) - 1 else sim[i]
        depths[i] = (left_peak - sim[i]) + (right_peak - sim[i])

    # 阈值：平均值 + 0.5 * 标准差（可按需调整策略）
    mean_depth = sum(depths) / len(depths)
    variance = sum((d - mean_depth) ** 2 for d in depths) / max(1, len(depths) - 1)
    std_depth = math.sqrt(variance)
    threshold = mean_depth + 0.5 * std_depth

    boundaries: List[int] = [i for i, d in enumerate(depths) if d >= threshold]
    return boundaries


def chunk_by_boundaries(
    sentences: List[str],
    boundaries: List[int],
    min_chars: int,
    max_chars: int,
) -> List[str]:
    chunks: List[str] = []
    candidate_boundaries = set(boundaries)

    # 贪心装箱：优先使用语义边界，同时满足大小约束
    current = []
    current_len = 0
    for i, s in enumerate(sentences):
        s_len = len(s)
        if current_len + s_len > max_chars and current:
            chunks.append("".join(current).strip())
            current = []
            current_len = 0

        current.append(s if s.endswith("\n") else s + "\n")
        current_len += len(current[-1])

        if i in candidate_boundaries and current_len >= min_chars:
            chunks.append("".join(current).strip())
            current = []
            current_len = 0

    if current:
        if chunks and len("".join(current)) < min_chars:
            # 若尾块过小，则与上一块合并
            chunks[-1] = (chunks[-1] + "\n" + "".join(current)).strip()
        else:
            chunks.append("".join(current).strip())

    # 清理：去除空块
    chunks = [c for c in chunks if c]
    return chunks


def split_text_to_chunks(
    text: str,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
    tokenizer: Callable[[str], List[str]] = tokenize,
) -> List[str]:
    """对纯文本进行语义分块。

    - 先进行句子切分；
    - 使用 TF-IDF 表示句子，再用滑动窗口计算相邻语块相似度；
    - 根据“深度”得分确定语义边界；
    - 在边界基础上进行最小/最大字符数的约束式装箱。
    """
    sentences = sentence_tokenize(text)
    if not sentences:
        return []
    vocabulary, tokenized = build_vocabulary(sentences, tokenizer)
    tfidf_vectors = compute_tfidf(tokenized, vocabulary)
    boundaries = texttiling_boundaries(sentences, tfidf_vectors, window_size, smoothing_width)
    return chunk_by_boundaries(sentences, boundaries, min_chars, max_chars)

def split_file_to_chunks(
    path: str,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
    tokenizer: Callable[[str], List[str]] = tokenize,
) -> List[str]:
    """从文件读取文本并进行语义分块。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return split_text_to_chunks(
        text=text,
        min_chars=min_chars,
        max_chars=max_chars,
        window_size=window_size,
        smoothing_width=smoothing_width,
        tokenizer=tokenizer,
    )


def read_docx_text(path: str) -> str:
    """读取 .docx 文本内容。

    依赖 python-docx；若未安装，将抛出友好错误提示。
    """
    if Document is None:
        raise RuntimeError("需要安装 python-docx 才能读取 .docx 文件，请先执行: pip install python-docx")
    doc = Document(path)
    # 将每段落以换行相接，保留基本段落结构
    return "\n".join(p.text for p in doc.paragraphs)


def split_docx_to_chunks(
    path: str,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
    tokenizer: Callable[[str], List[str]] = tokenize,
) -> List[str]:
    """对 .docx 文件进行语义分块。"""
    text = read_docx_text(path)
    return split_text_to_chunks(
        text=text,
        min_chars=min_chars,
        max_chars=max_chars,
        window_size=window_size,
        smoothing_width=smoothing_width,
        tokenizer=tokenizer,
    )


def save_chunks_to_jsonl(chunks: List[str], output_path: str, source_file_path: str = None) -> None:
    """将分块结果保存为 JSONL（每行一个 JSON）。
    
    Args:
        chunks: 分块文本列表
        output_path: 输出文件路径
        source_file_path: 源文件路径（可选，用于元数据）
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, c in enumerate(chunks):
            obj = {
                "index": i, 
                "chars": len(c), 
                "text": c
            }
            # 如果提供了源文件路径，添加到元数据中
            if source_file_path:
                obj["source_file"] = source_file_path
            f.write(json.dumps(obj, ensure_ascii=False))
            f.write("\n")


def main() -> None:
    """示例入口：读取指定 .docx，进行语义分块并保存为 JSONL。

    说明：不使用命令行参数，所有参数在此处直接设置。
    """
    input_path = "./知识库/政策文件/涉藏舆情研究相关政策.docx"
    output_path = "output/语义分割.jsonl"

    # 可按需调整这些参数
    min_chars = 400
    max_chars = 800
    window_size = 6
    smoothing_width = 2

    # 将相对路径解析为绝对路径：优先当前工作目录，其次脚本所在目录
    def _resolve_path(p: str) -> str:
        if os.path.isabs(p):
            return p
        candidates = [
            os.path.join(os.getcwd(), p),
            os.path.join(os.path.dirname(__file__), p),
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        # 默认返回基于 CWD 的绝对路径（即使不存在也便于报错显示）
        return os.path.abspath(os.path.join(os.getcwd(), p))

    input_abs = _resolve_path(input_path)
    if not os.path.exists(input_abs):
        raise FileNotFoundError(f"未找到输入文件: {input_path} -> {input_abs}")

    chunks = split_docx_to_chunks(
        path=input_abs,
        min_chars=min_chars,
        max_chars=max_chars,
        window_size=window_size,
        smoothing_width=smoothing_width,
    )

    save_chunks_to_jsonl(chunks, output_path, input_path)


if __name__ == "__main__":
    main()


