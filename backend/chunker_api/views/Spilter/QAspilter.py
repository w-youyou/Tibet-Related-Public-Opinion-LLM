#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
面向问答类语料的 RAG 文本分割器（仅抽取 Q/A 对），输出 JSONL。

功能：
- 支持输入 .docx（含段落与两列表格）、.pdf 与 .txt（按行）
- 识别“问/答”以及疑问句样式，构造稳健的 Q/A 对
- 输出 JSONL：每行包含 id、content、metadata（其中 content 为字符串，合并问与答）

使用：
直接运行脚本，按需修改文件内常量 DEFAULT_INPUT_PATH、DEFAULT_OUTPUT_PATH、PRESERVE_LINE_BREAKS

依赖：
- .docx 解析依赖 python-docx（仅当输入为 .docx 时需要）
- .pdf 解析建议使用 pdfplumber（仅当输入为 .pdf 时需要）
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

# 直接导入必需依赖（未安装将抛出 ImportError）
import docx  # type: ignore
import pdfplumber  # type: ignore
import pytesseract  # type: ignore

# 固定配置（无需命令行参数）
# - DEFAULT_INPUT_PATH 可为单个文件（.docx/.pdf/.txt）或目录；为目录时将递归处理
# - DEFAULT_OUTPUT_PATH：若输入为单文件，则为输出 JSONL 文件；若输入为目录，则作为输出根目录
DEFAULT_INPUT_PATH = r"D:\\Code\\Python\\langchain\\知识库\\咨询记录"        # 可改为目录，例如 r"D:\\Code\\Python\\langchain\\知识库\\咨询记录"
DEFAULT_OUTPUT_PATH = "output/qa.jsonl"  # 单文件输出路径；或目录批处理的输出根目录
PRESERVE_LINE_BREAKS = True               # True: 保留答案换行；False: 合并为单行
SUPPORTED_EXTS = {".docx", ".doc", ".pdf", ".txt"}  # 支持的输入文件类型



def normalize_text(text: str) -> str:
    return (text or "").replace("\r", "").strip()


def is_empty(text: str) -> bool:
    return len(normalize_text(text)) == 0


HEADING_CN_NUM = "一二三四五六七八九十百千万〇零壹贰叁肆伍陆柒捌玖拾"  # 不再用于标题识别


def looks_like_question(text: str) -> bool:
    t = normalize_text(text)
    if not t:
        return False
    if re.match(r"^[\s]*([问QＱ][:：]|(问|问题)[：:]\s*)", t):
        return True
    if len(t) <= 120 and t.endswith(("?", "？")):
        return True
    return False


def looks_like_answer(text: str) -> bool:
    t = normalize_text(text)
    if not t:
        return False
    return bool(re.match(r"^[\s]*((答|答复|解答|回复)[：:]|[答AＡ][:：])", t))


def is_question_sentence(text: str) -> bool:
    t = normalize_text(text)
    return bool(t) and t.endswith(("?", "？"))


def strip_qa_prefix(text: str) -> str:
    t = normalize_text(text)
    return re.sub(r"^[\s]*((问|问题|Q|Ｑ|答|答复|解答|回复|A|Ａ)[：:])\s*", "", t, count=1)


@dataclass
class ParagraphItem:
    text: str
    style_name: str


@dataclass
class QAItem:
    qa_id: int
    question: str
    answer: str
    section: Optional[str] = None


def read_docx_paragraphs(file_path: str) -> List[ParagraphItem]:
    document = docx.Document(file_path)

    from docx.oxml.text.paragraph import CT_P  # type: ignore
    from docx.oxml.table import CT_Tbl  # type: ignore
    from docx.text.paragraph import Paragraph  # type: ignore
    from docx.table import Table  # type: ignore

    items: List[ParagraphItem] = []

    def append_paragraph(p: "Paragraph") -> None:
        text = normalize_text(p.text)
        if not text:
            return
        style = getattr(getattr(p, "style", None), "name", "") or ""
        items.append(ParagraphItem(text=text, style_name=style))

    def append_table(tbl: "Table") -> None:
        header_skipped = False
        if tbl.rows and len(tbl.rows[0].cells) >= 2:
            left0 = normalize_text(tbl.rows[0].cells[0].text)
            right0 = normalize_text(tbl.rows[0].cells[1].text)
            if re.search(r"问题|问", left0) and re.search(r"答|答复|解答|回复", right0):
                header_skipped = True
        for r_idx, row in enumerate(tbl.rows):
            if len(row.cells) < 2:
                cell_text = normalize_text(" ".join(c.text for c in row.cells))
                if cell_text:
                    items.append(ParagraphItem(text=cell_text, style_name="TableRow"))
                continue
            if header_skipped and r_idx == 0:
                continue
            q_raw = normalize_text(row.cells[0].text)
            a_raw = normalize_text(row.cells[1].text)
            if not q_raw and not a_raw:
                continue
            if looks_like_question(q_raw) or is_question_sentence(q_raw):
                items.append(ParagraphItem(text=f"问：{q_raw}", style_name="TableQuestion"))
                if a_raw:
                    items.append(ParagraphItem(text=f"答：{a_raw}", style_name="TableAnswer"))
                continue
            if looks_like_answer(a_raw):
                items.append(ParagraphItem(text=f"问：{q_raw}", style_name="TableQuestion"))
                items.append(ParagraphItem(text=f"{a_raw}", style_name="TableAnswer"))
                continue
            if q_raw:
                items.append(ParagraphItem(text=q_raw, style_name="TableCellLeft"))
            if a_raw:
                items.append(ParagraphItem(text=a_raw, style_name="TableCellRight"))

    body = document._element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            append_paragraph(Paragraph(child, document))
        elif isinstance(child, CT_Tbl):
            append_table(Table(child, document))

    return items


def read_doc_paragraphs(file_path: str) -> List[ParagraphItem]:
    """读取.doc文件的段落"""
    try:
        import win32com.client
        import pythoncom
        import os
        
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            print(f"文件不存在: {abs_path}")
            return []
        
        # 初始化COM组件
        pythoncom.CoInitialize()
        
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        
        doc = word.Documents.Open(abs_path)
        
        # 按段落读取，保持段落结构
        items: List[ParagraphItem] = []
        for paragraph in doc.Paragraphs:
            text = paragraph.Range.Text.strip()
            if text:  # 只添加非空段落
                normalized_text = normalize_text(text)
                if normalized_text:
                    items.append(ParagraphItem(text=normalized_text, style_name="DOC"))
        
        doc.Close()
        word.Quit()
        
        return items
    except Exception as e:
        print(f"读取.doc文件失败: {e}")
        return []
    finally:
        try:
            if 'word' in locals():
                word.Quit()
            # 清理COM组件
            pythoncom.CoUninitialize()
        except:
            pass


def read_txt_paragraphs(file_path: str) -> List[ParagraphItem]:
    items: List[ParagraphItem] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            t = normalize_text(line)
            if not t:
                continue
            items.append(ParagraphItem(text=t, style_name=""))
    return items


def read_pdf_paragraphs(file_path: str) -> List[ParagraphItem]:
    """读取 PDF 文本为段落序列。

    策略：
    1) 首选使用 pdfplumber 的 extract_text()
    2) 若页面无可提取文本（扫描版/图片型 PDF），尝试使用 pytesseract 对页面位图进行 OCR
    3) 将得到的文本按行切分为 ParagraphItem
    """
    items: List[ParagraphItem] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not normalize_text(text):
                # 当文本抽取为空，尝试 OCR
                try:
                    # 将页面渲染为图像（PIL Image），再送入 OCR
                    pil_image = page.to_image(resolution=300).original
                    text = pytesseract.image_to_string(pil_image, lang="chi_sim+eng") or ""
                except Exception as ocr_exc:
                    # OCR 失败则保持为空，后续按空文本处理（即跳过）
                    sys.stderr.write(f"[WARN] OCR 失败，跳过该页：{ocr_exc}\n")
                    text = ""

            for line in (text.splitlines() if text else []):
                t = normalize_text(line)
                if not t:
                    continue
                items.append(ParagraphItem(text=t, style_name="PDF"))
    return items


def extract_qa(
    paragraphs: List[ParagraphItem],
    preserve_line_breaks: bool = True,
) -> Tuple[List[QAItem], str]:
    """从段落序列抽取问答对，并返回问答对列表与引言文本。

    变更：删除标题识别逻辑；在遇到首个问答对之前的非空文本合并为说明 `intro`，
    在写出阶段附加到每条记录的 `meta.intro`，便于检索时提供上下文而不污染问答内容。
    """
    qa_items: List[QAItem] = []
    current_section: Optional[str] = None  # 保留字段，但不再从标题推断
    current_question: Optional[str] = None
    current_answer_parts: List[str] = []
    intro_parts: List[str] = []
    next_id = 1

    def flush_current():
        nonlocal next_id, current_question, current_answer_parts
        if not current_question and not current_answer_parts:
            return
        question_text = normalize_text(current_question or "")
        answer_text = ("\n" if preserve_line_breaks else " ").join(
            [p for p in current_answer_parts if normalize_text(p)]
        ).strip()
        if question_text or answer_text:
            qa_items.append(
                QAItem(
                    qa_id=next_id,
                    question=question_text,
                    answer=answer_text,
                    section=current_section,
                )
            )
            next_id += 1

    for para in paragraphs:
        text = para.text
        style = para.style_name

        if looks_like_question(text):
            flush_current()
            current_question = strip_qa_prefix(text)
            current_answer_parts = []
            continue

        if looks_like_answer(text):
            if current_question is None:
                current_question = ""
                current_answer_parts = []
            current_answer_parts.append(strip_qa_prefix(text))
            continue

        if current_question is not None:
            current_answer_parts.append(text)
            continue

        # 未进入 QA 模式，但可能是独立疑问句，作为 question 开启
        if is_question_sentence(text):
            flush_current()
            current_question = text
            current_answer_parts = []
            continue

        # 仍未进入 QA：将文本收集为 intro
        if normalize_text(text):
            intro_parts.append(text)

    flush_current()
    intro_text = ("\n" if preserve_line_breaks else " ").join(intro_parts).strip()
    return qa_items, intro_text


def write_jsonl(
    qa_items: List[QAItem],
    output_path: str,
    *,
    source_filename: Optional[str] = None,
    source_file_path: Optional[str] = None,
    intro_text: Optional[str] = None,
    append: bool = False,
) -> None:
    """将一批 QA 记录写入 JSONL 文件。

    参数：
    - output_path: 目标 JSONL 文件路径
    - source_filename: 该批记录的来源文件名（用于 meta）
    - append: 是否以追加方式写入；目录批处理时建议为 True
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    mode = "a" if append else "w"
    with open(output_path, mode, encoding="utf-8") as f:
        for item in qa_items:
            # 构建 metadata，过滤掉 None 值（Chroma 不接受 None）
            metadata = {}
            if item.section is not None:
                metadata["section"] = item.section
            if source_filename is not None:
                metadata["source_filename"] = source_filename
            if intro_text is not None:
                metadata["intro"] = intro_text
            # 如果提供了源文件路径，添加到元数据中
            if source_file_path is not None:
                metadata["source_file"] = source_file_path

            parts = []
            if normalize_text(item.question):
                parts.append(f"问：{item.question}")
            if normalize_text(item.answer):
                parts.append(f"答：{item.answer}")
            content_text = "\n".join(parts).strip()

            record = {
                "id": item.qa_id,
                "content": content_text,
                "metadata": metadata,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run(
    input_path: str = DEFAULT_INPUT_PATH,
    output_path: str = DEFAULT_OUTPUT_PATH,
    preserve_line_breaks: bool = PRESERVE_LINE_BREAKS,
) -> int:
    """运行主流程。

    行为：
    - 若 input_path 为目录：递归处理其中所有支持类型文件，输出到 output_path 目录下保持相对结构的 .jsonl 文件。
    - 若 input_path 为文件：读取并抽取 Q/A，输出到 output_path 文件。
    """

    if not os.path.exists(input_path):
        sys.stderr.write(f"[ERROR] 输入路径不存在：{input_path}\n")
        return 2

    # 目录批处理模式：聚合写入到同一个 JSONL 文件
    if os.path.isdir(input_path):
        # 若输出文件已存在，先删除，避免追加造成重复
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception:
            pass
        total_files = 0
        total_pairs = 0

        for root, _, files in os.walk(input_path):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext not in SUPPORTED_EXTS:
                    continue
                in_file = os.path.join(root, name)

                try:
                    if ext == ".docx":
                        paragraphs = read_docx_paragraphs(in_file)
                    elif ext == ".doc":
                        paragraphs = read_doc_paragraphs(in_file)
                    elif ext == ".pdf":
                        paragraphs = read_pdf_paragraphs(in_file)
                    else:
                        paragraphs = read_txt_paragraphs(in_file)

                    qa_items, intro_text = extract_qa(paragraphs, preserve_line_breaks=preserve_line_breaks)
                    write_jsonl(
                        qa_items,
                        output_path,
                        source_filename=os.path.basename(in_file),
                        source_file_path=in_file,
                        intro_text=intro_text,
                        append=True,
                    )
                    print(f"[OK] {in_file} -> {output_path}（追加），{len(qa_items)} 组")
                    total_files += 1
                    total_pairs += len(qa_items)
                except Exception as e:
                    sys.stderr.write(f"[WARN] 处理失败，已跳过：{in_file}: {e}\n")

        print(f"完成。输出文件：{output_path}。共处理文件 {total_files} 个，问答对 {total_pairs} 组。")
        return 0

    # 单文件处理模式
    ext = os.path.splitext(input_path)[1].lower()
    if ext not in SUPPORTED_EXTS:
        sys.stderr.write(f"[ERROR] 不支持的文件类型：{ext}，支持 {sorted(SUPPORTED_EXTS)}\n")
        return 2

    try:
        if ext == ".docx":
            paragraphs = read_docx_paragraphs(input_path)
        elif ext == ".doc":
            paragraphs = read_doc_paragraphs(input_path)
        elif ext == ".pdf":
            paragraphs = read_pdf_paragraphs(input_path)
        else:
            paragraphs = read_txt_paragraphs(input_path)
    except Exception as e:
        sys.stderr.write(f"[ERROR] 读取失败：{e}\n")
        return 2

    qa_items, intro_text = extract_qa(paragraphs, preserve_line_breaks=preserve_line_breaks)
    write_jsonl(qa_items, output_path, source_filename=os.path.basename(input_path), source_file_path=input_path, intro_text=intro_text)
    print(f"已生成问答对：{output_path}，共 {len(qa_items)} 组")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())


