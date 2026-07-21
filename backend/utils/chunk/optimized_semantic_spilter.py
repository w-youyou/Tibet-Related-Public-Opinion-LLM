from langchain_experimental.text_splitter import SemanticChunker
import re
import math
import os
import json
from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Callable, Set
try:
    from docx import Document  # python-docx
except Exception:  # 延迟导入错误到使用时提示
    Document = None  # type: ignore

try:
    import PyPDF2
    import pdfplumber
except Exception:  # 延迟导入错误到使用时提示
    PyPDF2 = None
    pdfplumber = None


def sentence_tokenize(text: str) -> List[str]:
    """将原始纯文本切分为句子，适用于中英文混排等场景。"""
    if not text:
        return []

    # 归一化换行符
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')

    # 使用带捕获组的正则分隔，使得分隔符（标点）可被保留
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

    # 后处理：将极短的尾随"句子"并入前句，避免碎片
    merged: List[str] = []
    for sent in sentences:
        if merged and len(sent) < 4:
            merged[-1] = (merged[-1] + (" " if merged[-1] and not merged[-1].endswith("\n") else "") + sent).strip()
        else:
            merged.append(sent)
    return merged


# 优化的分词器：只保留重要词汇，减少词汇表大小
_word_re = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", re.UNICODE)

def optimized_tokenize(text: str) -> List[str]:
    """优化的分词器：只保留重要词汇，减少词汇表大小"""
    tokens: List[str] = []
    for m in _word_re.finditer(text):
        w = m.group(0)
        # 过滤掉单字符和数字
        if len(w) == 1 and ord(w) >= 0x4e00 and ord(w) <= 0x9fff:
            tokens.append(w)  # 保留中文字符
        elif len(w) > 1:  # 只保留长度大于1的词
            tokens.append(w.lower())
    return tokens


def build_optimized_vocabulary(sentences: List[str], tokenizer: Callable[[str], List[str]]) -> Tuple[Dict[str, int], List[List[str]]]:
    """优化的词汇表构建：限制词汇表大小"""
    tokenized: List[List[str]] = [tokenizer(s) for s in sentences]
    
    # 统计词频，只保留高频词
    word_freq = Counter()
    for toks in tokenized:
        for t in toks:
            word_freq[t] += 1
    
    # 只保留出现频率大于1的词，限制词汇表大小
    min_freq = max(1, len(sentences) // 1000)  # 动态调整最小频率
    vocab: Dict[str, int] = {}
    for word, freq in word_freq.items():
        if freq >= min_freq:
            vocab[word] = len(vocab)
    
    # 重新分词，过滤掉不在词汇表中的词
    filtered_tokenized = []
    for toks in tokenized:
        filtered_toks = [t for t in toks if t in vocab]
        if filtered_toks:  # 只保留非空的句子
            filtered_tokenized.append(filtered_toks)
    
    return vocab, filtered_tokenized


def compute_simple_tfidf(tokenized_sentences: List[List[str]], vocabulary: Dict[str, int]) -> List[Dict[int, float]]:
    """简化的TF-IDF计算：使用更简单的权重"""
    num_docs = len(tokenized_sentences)
    if num_docs == 0:
        return []

    # 文档频次（DF）
    doc_freq: defaultdict[int, int] = defaultdict(int)
    for toks in tokenized_sentences:
        unique_terms = set(toks)
        for t in unique_terms:
            doc_freq[vocabulary[t]] += 1

    # 简化的IDF计算
    idf: Dict[int, float] = {}
    for term_index, df in doc_freq.items():
        idf[term_index] = math.log(num_docs / df) if df > 0 else 0

    # 简化的TF-IDF计算
    tfidf_vectors: List[Dict[int, float]] = []
    for toks in tokenized_sentences:
        counts = Counter(vocabulary[t] for t in toks)
        vec: Dict[int, float] = {}
        for term_index, tf in counts.items():
            # 使用简单的TF-IDF公式
            vec[term_index] = tf * idf.get(term_index, 0.0)
        
        # 简化的归一化
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        for k in list(vec.keys()):
            vec[k] /= norm
        tfidf_vectors.append(vec)
    return tfidf_vectors


def jaccard_similarity(a: Dict[int, float], b: Dict[int, float]) -> float:
    """使用Jaccard相似度替代余弦相似度，计算更快"""
    if not a or not b:
        return 0.0
    
    # 获取两个向量的键集合
    keys_a = set(a.keys())
    keys_b = set(b.keys())
    
    # 计算交集和并集
    intersection = keys_a & keys_b
    union = keys_a | keys_b
    
    if not union:
        return 0.0
    
    # 计算加权Jaccard相似度
    intersection_sum = sum(min(a[k], b[k]) for k in intersection)
    union_sum = sum(max(a.get(k, 0), b.get(k, 0)) for k in union)
    
    return intersection_sum / union_sum if union_sum > 0 else 0.0


def precompute_windows(tfidf_vectors: List[Dict[int, float]], window_size: int) -> List[Dict[int, float]]:
    """预计算所有窗口的向量，避免重复计算"""
    if not tfidf_vectors:
        return []
    
    windows = []
    for i in range(len(tfidf_vectors) - window_size + 1):
        # 聚合窗口内的向量
        agg: Dict[int, float] = defaultdict(float)
        for j in range(i, i + window_size):
            for k, v in tfidf_vectors[j].items():
                agg[k] += v
        
        # 归一化
        norm = math.sqrt(sum(v * v for v in agg.values())) or 1.0
        for k in list(agg.keys()):
            agg[k] /= norm
        windows.append(dict(agg))
    
    return windows


def precompute_peaks(sim: List[float]) -> Tuple[List[float], List[float]]:
    """预计算所有位置的左右峰值，避免重复计算"""
    n = len(sim)
    left_peaks = [0.0] * n
    right_peaks = [0.0] * n
    
    # 计算左峰值
    for i in range(n):
        if i == 0:
            left_peaks[i] = sim[i]
        else:
            left_peaks[i] = max(left_peaks[i-1], sim[i])
    
    # 计算右峰值
    for i in range(n-1, -1, -1):
        if i == n-1:
            right_peaks[i] = sim[i]
        else:
            right_peaks[i] = max(right_peaks[i+1], sim[i])
    
    return left_peaks, right_peaks


def optimized_texttiling_boundaries(
    sentences: List[str],
    tfidf_vectors: List[Dict[int, float]],
    window_size: int = 6,
    smoothing_width: int = 2,
) -> List[int]:
    """优化的TextTiling边界检测"""
    n = len(sentences)
    if n <= 1:
        return []

    # 预计算所有窗口
    windows = precompute_windows(tfidf_vectors, window_size)
    
    # 计算相似度
    sim: List[float] = []
    for gap in range(n - 1):
        if gap < len(windows) and gap + 1 < len(windows):
            sim.append(jaccard_similarity(windows[gap], windows[gap + 1]))
        else:
            sim.append(0.0)

    if not sim:
        return []

    # 滑动平均平滑
    if smoothing_width > 0:
        smoothed: List[float] = []
        for i in range(len(sim)):
            a = max(0, i - smoothing_width)
            b = min(len(sim), i + smoothing_width + 1)
            smoothed.append(sum(sim[a:b]) / (b - a))
        sim = smoothed

    # 预计算峰值
    left_peaks, right_peaks = precompute_peaks(sim)
    
    # 计算深度得分
    depths: List[float] = [0.0] * len(sim)
    for i in range(1, len(sim) - 1):
        depths[i] = (left_peaks[i] - sim[i]) + (right_peaks[i] - sim[i])

    # 简化的阈值计算
    mean_depth = sum(depths) / len(depths)
    threshold = mean_depth * 1.2  # 使用固定倍数而非标准差

    boundaries: List[int] = [i for i, d in enumerate(depths) if d >= threshold]
    return boundaries


def chunk_by_boundaries(
    sentences: List[str],
    boundaries: List[int],
    min_chars: int,
    max_chars: int,
) -> List[str]:
    """基于边界进行分块"""
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


def process_in_chunks(
    sentences: List[str],
    chunk_size: int = 1000,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
) -> List[str]:
    """分块处理大文档，避免内存问题"""
    if len(sentences) <= chunk_size:
        # 小文档直接处理
        return process_single_chunk(sentences, min_chars, max_chars, window_size, smoothing_width)
    
    # 大文档分块处理
    all_chunks = []
    for i in range(0, len(sentences), chunk_size):
        chunk_sentences = sentences[i:i+chunk_size]
        chunk_results = process_single_chunk(chunk_sentences, min_chars, max_chars, window_size, smoothing_width)
        all_chunks.extend(chunk_results)
    
    return all_chunks


def process_single_chunk(
    sentences: List[str],
    min_chars: int,
    max_chars: int,
    window_size: int,
    smoothing_width: int,
) -> List[str]:
    """处理单个文档块"""
    if not sentences:
        return []
    
    # 构建词汇表和TF-IDF向量
    vocabulary, tokenized = build_optimized_vocabulary(sentences, optimized_tokenize)
    if not vocabulary:
        return [" ".join(sentences)]  # 如果没有词汇，返回整个文本
    
    tfidf_vectors = compute_simple_tfidf(tokenized, vocabulary)
    boundaries = optimized_texttiling_boundaries(sentences, tfidf_vectors, window_size, smoothing_width)
    return chunk_by_boundaries(sentences, boundaries, min_chars, max_chars)


def split_text_to_chunks(
    text: str,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
    chunk_size: int = 1000,
) -> List[str]:
    """优化的文本语义分块"""
    sentences = sentence_tokenize(text)
    if not sentences:
        return []
    
    return process_in_chunks(
        sentences=sentences,
        chunk_size=chunk_size,
        min_chars=min_chars,
        max_chars=max_chars,
        window_size=window_size,
        smoothing_width=smoothing_width,
    )


def split_file_to_chunks(
    path: str,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
    chunk_size: int = 1000,
) -> List[str]:
    """从文件读取文本并进行优化的语义分块"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return split_text_to_chunks(
        text=text,
        min_chars=min_chars,
        max_chars=max_chars,
        window_size=window_size,
        smoothing_width=smoothing_width,
        chunk_size=chunk_size,
    )


def read_docx_text(path: str) -> str:
    """读取 .docx 文本内容"""
    if Document is None:
        raise RuntimeError("需要安装 python-docx 才能读取 .docx 文件，请先执行: pip install python-docx")
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def read_pdf_text(path: str) -> str:
    """读取 PDF 文本内容"""
    if pdfplumber is None and PyPDF2 is None:
        raise RuntimeError("需要安装 pdfplumber 或 PyPDF2 才能读取 PDF 文件，请先执行: pip install pdfplumber PyPDF2")
    
    text_content = ""
    
    try:
        # 首先尝试使用 pdfplumber（效果更好）
        if pdfplumber is not None:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
        else:
            # 备用方案：使用 PyPDF2
            with open(path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
    except Exception as e:
        raise RuntimeError(f"PDF文本提取失败: {e}")
    
    return text_content.strip()


def split_docx_to_chunks(
    path: str,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
    chunk_size: int = 1000,
) -> List[str]:
    """对 .docx 文件进行优化的语义分块"""
    text = read_docx_text(path)
    return split_text_to_chunks(
        text=text,
        min_chars=min_chars,
        max_chars=max_chars,
        window_size=window_size,
        smoothing_width=smoothing_width,
        chunk_size=chunk_size,
    )


def read_doc_text(path: str) -> str:
    """读取 .doc 文本内容"""
    try:
        import win32com.client
        import pythoncom
        import os
        
        # 转换为绝对路径
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"文件不存在: {abs_path}")
        
        # 初始化COM组件
        pythoncom.CoInitialize()
        
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        
        doc = word.Documents.Open(abs_path)
        
        # 按段落读取，保持段落结构
        paragraphs = []
        for paragraph in doc.Paragraphs:
            text = paragraph.Range.Text.strip()
            if text:  # 只添加非空段落
                paragraphs.append(text)
        
        doc.Close()
        word.Quit()
        
        # 用换行符连接段落
        return '\n'.join(paragraphs)
    except Exception as e:
        raise RuntimeError(f"读取.doc文件失败: {e}")
    finally:
        try:
            if 'word' in locals():
                word.Quit()
            # 清理COM组件
            pythoncom.CoUninitialize()
        except:
            pass


def split_doc_to_chunks(
    path: str,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
    chunk_size: int = 1000,
) -> List[str]:
    """对 .doc 文件进行优化的语义分块"""
    text = read_doc_text(path)
    return split_text_to_chunks(
        text=text,
        min_chars=min_chars,
        max_chars=max_chars,
        window_size=window_size,
        smoothing_width=smoothing_width,
        chunk_size=chunk_size,
    )


def split_pdf_to_chunks(
    path: str,
    min_chars: int = 800,
    max_chars: int = 1800,
    window_size: int = 6,
    smoothing_width: int = 2,
    chunk_size: int = 1000,
) -> List[str]:
    """对 PDF 文件进行优化的语义分块"""
    text = read_pdf_text(path)
    return split_text_to_chunks(
        text=text,
        min_chars=min_chars,
        max_chars=max_chars,
        window_size=window_size,
        smoothing_width=smoothing_width,
        chunk_size=chunk_size,
    )


def save_chunks_to_jsonl(chunks: List[str], output_path: str, source_file_path: str = None) -> None:
    """将分块结果保存为 JSONL"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, c in enumerate(chunks):
            obj = {
                "id": i,
                "content": c,
                "metadata": {
                    "chars": len(c),
                    "source_file": source_file_path if source_file_path else None
                }
            }
            f.write(json.dumps(obj, ensure_ascii=False))
            f.write("\n")


def main() -> None:
    """示例入口：测试优化后的语义分块器"""
    input_path = r"./KnowledgeBase/5 一般文本/《税收征管操作规范(2023年版)》全文.pdf"
    output_path = "output/优化语义分割.jsonl"

    # 优化的参数设置
    min_chars = 400
    max_chars = 800
    window_size = 4  # 减小窗口大小
    smoothing_width = 1  # 减小平滑宽度
    chunk_size = 500  # 分块处理大小

    # 路径解析
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
        return os.path.abspath(os.path.join(os.getcwd(), p))

    input_abs = _resolve_path(input_path)
    if not os.path.exists(input_abs):
        raise FileNotFoundError(f"未找到输入文件: {input_path} -> {input_abs}")

    print("开始处理文档...")
    import time
    start_time = time.time()
    
    # 根据文件扩展名选择处理方式
    file_ext = os.path.splitext(input_abs)[1].lower()
    if file_ext == '.pdf':
        chunks = split_pdf_to_chunks(
            path=input_abs,
            min_chars=min_chars,
            max_chars=max_chars,
            window_size=window_size,
            smoothing_width=smoothing_width,
            chunk_size=chunk_size,
        )
    elif file_ext == '.docx':
        chunks = split_docx_to_chunks(
            path=input_abs,
            min_chars=min_chars,
            max_chars=max_chars,
            window_size=window_size,
            smoothing_width=smoothing_width,
            chunk_size=chunk_size,
        )
    elif file_ext == '.doc':
        chunks = split_doc_to_chunks(
            path=input_abs,
            min_chars=min_chars,
            max_chars=max_chars,
            window_size=window_size,
            smoothing_width=smoothing_width,
            chunk_size=chunk_size,
        )
    else:
        # 默认按文本文件处理
        chunks = split_file_to_chunks(
            path=input_abs,
            min_chars=min_chars,
            max_chars=max_chars,
            window_size=window_size,
            smoothing_width=smoothing_width,
            chunk_size=chunk_size,
        )

    end_time = time.time()
    processing_time = end_time - start_time
    
    save_chunks_to_jsonl(chunks, output_path, input_path)
    
    print(f"处理完成！")
    print(f"处理时间: {processing_time:.2f}秒")
    print(f"生成块数: {len(chunks)}")
    print(f"平均每块字符数: {sum(len(c) for c in chunks) / len(chunks) if chunks else 0:.0f}")


if __name__ == "__main__":
    main()
