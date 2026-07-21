import re
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from docx import Document
import fitz  # PyMuPDF for PDF processing


@dataclass
class LawTextChunk:
    """法律法规文本分块结果"""
    content: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LawSpilter:
    """法律法规文本分块器
    
    专门用于处理法律法规类文档，以"条"为最小单元进行分块：
    - 支持PDF和Word格式
    - 提取元数据：document_title、chapter、intro、file_name
    - 以"第X条"为分块边界
    """
    
    def __init__(self):
        # 定义分块模式
        self.patterns = [
            # 条：第一条、第二条等
            (r'^第[一二三四五六七八九十百千万\d]+条', 1, '条'),
        ]
        
        # 编译正则表达式
        self.compiled_patterns = [
            (re.compile(pattern), level, name) 
            for pattern, level, name in self.patterns
        ]
        
        # 章节模式
        self.chapter_pattern = re.compile(r'^第[一二三四五六七八九十百千万\d]+章')
        
        # 文档标题模式（通常在文档开头）
        self.title_pattern = re.compile(r'^.*法$|^.*条例$|^.*规定$|^.*办法$|^.*细则$')
    
    def split_text(self, text: str, file_name: str = "", file_path: str = None) -> List[LawTextChunk]:
        """将法律法规文本按"条"进行分块
        
        Args:
            text: 待分块的文本
            file_name: 文件名
            
        Returns:
            分块结果列表
        """
        if not text or not text.strip():
            return []
        
        # 提取文档元数据
        document_title, intro_content = self._extract_document_metadata(text)
        
        # 按行分割文本
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_chapter = ""
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                if current_chunk:
                    current_chunk.append("")
                continue
            
            # 检查是否是章节标题
            chapter_match = self.chapter_pattern.match(line)
            if chapter_match:
                current_chapter = line
                # 章节标题单独作为一个分块
                if current_chunk:
                    chunk_content = '\n'.join(current_chunk).strip()
                    if chunk_content:
                        # 构建 metadata，过滤掉 None 值（Chroma 不接受 None）
                        metadata = {}
                        if document_title is not None:
                            metadata["document_title"] = document_title
                        if current_chapter is not None:
                            metadata["chapter"] = current_chapter
                        if intro_content is not None:
                            metadata["intro"] = intro_content
                        if file_name is not None:
                            metadata["file_name"] = file_name
                        metadata["chunk_type"] = "content"
                        # 如果提供了文件路径，添加到元数据中
                        if file_path is not None:
                            metadata["source_file"] = file_path
                        chunks.append(LawTextChunk(
                            content=chunk_content,
                            metadata=metadata
                        ))
                current_chunk = [line]
                continue
            
            # 检查是否匹配"条"的模式
            matched = False
            for pattern, level, pattern_name in self.compiled_patterns:
                match = pattern.match(line)
                if match:
                    # 如果当前有未完成的分块，先保存它
                    if current_chunk:
                        chunk_content = '\n'.join(current_chunk).strip()
                        if chunk_content:
                            # 构建 metadata，过滤掉 None 值（Chroma 不接受 None）
                            metadata = {}
                            if document_title is not None:
                                metadata["document_title"] = document_title
                            if current_chapter is not None:
                                metadata["chapter"] = current_chapter
                            if intro_content is not None:
                                metadata["intro"] = intro_content
                            if file_name is not None:
                                metadata["file_name"] = file_name
                            metadata["chunk_type"] = "content"
                            # 如果提供了文件路径，添加到元数据中
                            if file_path is not None:
                                metadata["source_file"] = file_path
                            chunks.append(LawTextChunk(
                                content=chunk_content,
                                metadata=metadata
                            ))
                    
                    # 开始新的分块
                    current_chunk = [line]
                    matched = True
                    break
            
            if not matched:
                # 如果当前行不匹配任何模式，添加到当前分块
                current_chunk.append(line)
        
        # 处理最后一个分块
        if current_chunk:
            chunk_content = '\n'.join(current_chunk).strip()
            if chunk_content:
                # 构建 metadata，过滤掉 None 值（Chroma 不接受 None）
                metadata = {}
                if document_title is not None:
                    metadata["document_title"] = document_title
                if current_chapter is not None:
                    metadata["chapter"] = current_chapter
                if intro_content is not None:
                    metadata["intro"] = intro_content
                if file_name is not None:
                    metadata["file_name"] = file_name
                metadata["chunk_type"] = "content"
                # 如果提供了文件路径，添加到元数据中
                if file_path is not None:
                    metadata["source_file"] = file_path
                chunks.append(LawTextChunk(
                    content=chunk_content,
                    metadata=metadata
                ))
        
        return chunks
    
    def _extract_document_metadata(self, text: str) -> Tuple[str, str]:
        """提取文档标题和介绍性内容
        
        Args:
            text: 文本内容
            
        Returns:
            (文档标题, 介绍性内容)
        """
        lines = text.split('\n')
        document_title = ""
        intro_content = []
        
        # 查找文档标题（通常在文档开头，以"法"、"条例"等结尾）
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 跳过新华社等新闻来源
            if line.startswith("新华社") or line.startswith("新华网"):
                continue
            
            # 检查是否是文档标题
            if self.title_pattern.match(line):
                document_title = line
                break
        
        # 如果没有找到标题，使用第一行非空内容作为标题
        if not document_title:
            for line in lines:
                line = line.strip()
                if line and not line.startswith("新华社") and not line.startswith("新华网"):
                    document_title = line
                    break
        
        # 提取介绍性内容（从标题到第一章之间的内容）
        found_first_chapter = False
        collecting_intro = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if collecting_intro:
                    intro_content.append("")
                continue
            
            # 检查是否遇到第一章
            if self.chapter_pattern.match(line):
                found_first_chapter = True
                break
            
            # 如果已经找到标题，开始收集介绍性内容
            if line == document_title:
                collecting_intro = True
                continue
            
            if collecting_intro:
                intro_content.append(line)
        
        intro = '\n'.join(intro_content).strip() if intro_content else ""
        return document_title, intro
    
    def read_docx(self, file_path: str) -> str:
        """读取Word文档内容
        
        Args:
            file_path: Word文档路径
            
        Returns:
            文档文本内容
        """
        try:
            doc = Document(file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text.strip())
            
            return '\n'.join(text_content)
        except Exception as e:
            print(f"读取Word文档失败: {e}")
            return ""
    
    def read_pdf(self, file_path: str) -> str:
        """读取PDF文档内容
        
        Args:
            file_path: PDF文档路径
            
        Returns:
            文档文本内容
        """
        try:
            doc = fitz.open(file_path)
            text_content = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_content.append(page_text.strip())
            
            doc.close()
            return '\n'.join(text_content)
        except Exception as e:
            print(f"读取PDF文档失败: {e}")
            return ""
    
    def read_doc(self, file_path: str) -> str:
        """读取.doc文档内容
        
        Args:
            file_path: .doc文档路径
            
        Returns:
            文档文本内容
        """
        try:
            import win32com.client
            import pythoncom
            import os
            
            # 转换为绝对路径
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                print(f"文件不存在: {abs_path}")
                return ""
            
            # 初始化COM组件
            pythoncom.CoInitialize()
            
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            
            # 使用绝对路径打开文档
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
            print(f"读取.doc文档失败: {e}")
            return ""
        finally:
            try:
                if 'word' in locals():
                    word.Quit()
                # 清理COM组件
                pythoncom.CoUninitialize()
            except:
                pass
    
    def read_document(self, file_path: str) -> str:
        """读取文档内容（支持Word和PDF）
        
        Args:
            file_path: 文档路径
            
        Returns:
            文档文本内容
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.docx':
            return self.read_docx(file_path)
        elif file_ext == '.doc':
            return self.read_doc(file_path)
        elif file_ext == '.pdf':
            return self.read_pdf(file_path)
        else:
            print(f"不支持的文件格式: {file_ext}")
            return ""
    
    def save_to_jsonl(self, chunks: List[LawTextChunk], output_path: str):
        """将分块结果保存为JSONL格式
        
        Args:
            chunks: 分块列表
            output_path: 输出文件路径
        """
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, chunk in enumerate(chunks):
                # 构建完整的数据结构
                chunk_data = {
                    "id": i + 1,
                    "content": chunk.content,
                    "metadata": chunk.metadata
                }
                
                # 写入JSONL格式（每行一个JSON对象）
                f.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')
        
        print(f"分块结果已保存到: {output_path}")
        print(f"共保存 {len(chunks)} 个分块")
    
    def print_chunks(self, chunks: List[LawTextChunk], show_content: bool = False):
        """打印分块结果
        
        Args:
            chunks: 分块列表
            show_content: 是否显示完整内容
        """
        print(f"共找到 {len(chunks)} 个分块：\n")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"{i}. 分块 {i}")
            print(f"   文档标题: {chunk.metadata.get('document_title', '')}")
            print(f"   章节: {chunk.metadata.get('chapter', '')}")
            print(f"   文件名: {chunk.metadata.get('file_name', '')}")
            
            if show_content:
                content_lines = chunk.content.split('\n')
                for line in content_lines[:3]:  # 只显示前3行
                    print(f"   {line}")
                if len(content_lines) > 3:
                    print(f"   ...")
            print()
    
    def get_chunk_statistics(self, chunks: List[LawTextChunk]) -> Dict[str, Any]:
        """获取分块统计信息
        
        Args:
            chunks: 分块列表
            
        Returns:
            统计信息字典
        """
        statistics = {
            "total_chunks": len(chunks),
            "chapters": {},
            "articles_count": 0
        }
        
        for chunk in chunks:
            chapter = chunk.metadata.get('chapter', '无章节')
            if chapter not in statistics["chapters"]:
                statistics["chapters"][chapter] = 0
            statistics["chapters"][chapter] += 1
            
            # 统计"条"的数量
            if chunk.content.startswith("第") and "条" in chunk.content:
                statistics["articles_count"] += 1
        
        return statistics


def main():
    """测试函数"""
    print("开始测试法律法规文本分块功能")
    
    # 使用指定 PDF 文件路径进行测试
    file_path = os.path.join(
        "知识库",
        "2 法律类文本",
        "中华人民共和国企业所得税法.doc"
    )
    print(f"正在读取文档: {file_path}")
    
    splitter = LawSpilter()
    doc_text = splitter.read_document(file_path)
    if not doc_text:
        print("读取文档内容为空，无法分块。")
        return
    
    # 执行分块
    print("正在执行文本分块...")
    chunks = splitter.split_text(doc_text, os.path.basename(file_path), file_path)
    
    # 打印结果
    print("=== 分块结果 ===")
    splitter.print_chunks(chunks, show_content=True)
    
    # 统计信息
    print("\n=== 统计信息 ===")
    stats = splitter.get_chunk_statistics(chunks)
    print(f"总分块数: {stats['total_chunks']}")
    print(f"条文数量: {stats['articles_count']}")
    print("章节分布:")
    for chapter, count in stats['chapters'].items():
        print(f"  {chapter}: {count} 个分块")
    
    # 保存为JSONL格式
    output_path = "./output/法律法规测试.jsonl"
    print(f"\n正在保存结果到: {output_path}")
    splitter.save_to_jsonl(chunks, output_path)


if __name__ == "__main__":
    main()
