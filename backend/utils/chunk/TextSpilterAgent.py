#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能文本分割代理
根据文件夹路径自动选择合适的分割器进行处理
支持5种分割器：语义分割、表格分割、法律法规、政策公告、问答对
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# 导入所有分割器
# 使用优化后的语义分割器
from optimized_semantic_spilter import (
    split_text_to_chunks,
    split_file_to_chunks,
    split_docx_to_chunks,
    split_pdf_to_chunks,
)
from TableSpilter import TableSpilter
from LawSpilter import LawSpilter
from PolicyAnnouncementSpilter import PolicyAnnouncementSpilter
from QAspilter import run as qa_run


@dataclass
class ProcessingResult:
    """处理结果"""
    file_path: str
    splitter_type: str
    chunks: List[Dict[str, Any]]
    success: bool
    error_message: Optional[str] = None


class TextSpilterAgent:
    """智能文本分割代理
    
    根据文件夹路径自动选择分割器：
    - /知识库/5 一般文本 -> 语义分割
    - /知识库/1 政策公告类文本 -> PolicyAnnouncementSpilter
    - /知识库/2 法律类文本 -> LawSpilter
    - /知识库/3 问答类 -> QAspilter
    - /知识库/4 表格类文本 -> TableSpilter
    """
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.supported_extensions = {'.txt', '.docx', '.pdf', '.xlsx', '.xls'}
        
        # 初始化各分割器
        self.table_splitter = TableSpilter(rows_per_chunk=30)
        self.law_splitter = LawSpilter()
        self.policy_splitter = PolicyAnnouncementSpilter()
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 统计信息
        self.stats = {
            "total_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_chunks": 0,
            "splitter_usage": {},
            "file_types": {}
        }
    
    def detect_splitter_by_folder(self, file_path: str) -> str:
        """根据文件夹路径直接指定分割器类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            分割器类型：'semantic', 'table', 'law', 'policy', 'qa'
        """
        # 将路径转换为标准格式
        normalized_path = os.path.normpath(file_path).replace('\\', '/')
        
        # 直接根据文件夹路径指定分割器
        if 'KnowledgeBase/5 一般文本' in normalized_path or 'KnowledgeBase/5' in normalized_path:
            return 'semantic'
        elif 'KnowledgeBase/1 政策公告类文本' in normalized_path or 'KnowledgeBase/1' in normalized_path:
            return 'policy'
        elif 'KnowledgeBase/2 法律类文本' in normalized_path or 'KnowledgeBase/2' in normalized_path:
            return 'law'
        elif 'KnowledgeBase/3 问答类' in normalized_path or 'KnowledgeBase/3' in normalized_path:
            return 'qa'
        elif 'KnowledgeBase/4 表格类文本' in normalized_path or 'KnowledgeBase/4' in normalized_path:
            return 'table'
        
        # 默认使用语义分割
        return 'semantic'
    
    def process_semantic(self, file_path: str) -> ProcessingResult:
        """使用语义分割器处理文件"""
        try:
            if file_path.lower().endswith('.docx'):
                chunks = split_docx_to_chunks(
                    path=file_path,
                    min_chars=400,
                    max_chars=800,
                    window_size=6,
                    smoothing_width=2
                )
            elif file_path.lower().endswith('.pdf'):
                chunks = split_pdf_to_chunks(
                    path=file_path,
                    min_chars=400,
                    max_chars=800,
                    window_size=6,
                    smoothing_width=2
                )
            else:
                chunks = split_file_to_chunks(
                    path=file_path,
                    min_chars=400,
                    max_chars=800,
                    window_size=6,
                    smoothing_width=2
                )
            
            # 转换为统一格式
            result_chunks = []
            for i, chunk in enumerate(chunks):
                result_chunks.append({
                    "id": i + 1,
                    "content": chunk,
                    "metadata": {
                        "splitter_type": "semantic",
                        "source_file": file_path,
                        "chars": len(chunk)
                    }
                })
            
            return ProcessingResult(
                file_path=file_path,
                splitter_type="semantic",
                chunks=result_chunks,
                success=True
            )
        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                splitter_type="semantic",
                chunks=[],
                success=False,
                error_message=str(e)
            )
    
    def process_table(self, file_path: str) -> ProcessingResult:
        """使用表格分割器处理文件"""
        try:
            tables = self.table_splitter.read_any(file_path)
            all_chunks = []
            
            for table_name, rows in tables:
                chunks = self.table_splitter.split_table_rows(
                    rows=rows,
                    file_name=os.path.basename(file_path),
                    table_name=table_name,
                    file_path=file_path
                )
                all_chunks.extend(chunks)
            
            # 转换为统一格式
            result_chunks = []
            for i, chunk in enumerate(all_chunks):
                content_json = self.table_splitter.rows_to_records(chunk.content)
                result_chunks.append({
                    "id": i + 1,
                    "content": content_json,
                    "metadata": {
                        "splitter_type": "table",
                        "source_file": file_path,
                        **chunk.metadata
                    }
                })
            
            return ProcessingResult(
                file_path=file_path,
                splitter_type="table",
                chunks=result_chunks,
                success=True
            )
        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                splitter_type="table",
                chunks=[],
                success=False,
                error_message=str(e)
            )
    
    def process_law(self, file_path: str) -> ProcessingResult:
        """使用法律法规分割器处理文件"""
        try:
            doc_text = self.law_splitter.read_document(file_path)
            if not doc_text:
                raise ValueError("无法读取文档内容")
            
            chunks = self.law_splitter.split_text(
                text=doc_text,
                file_name=os.path.basename(file_path),
                file_path=file_path
            )
            
            # 转换为统一格式
            result_chunks = []
            for i, chunk in enumerate(chunks):
                result_chunks.append({
                    "id": i + 1,
                    "content": chunk.content,
                    "metadata": {
                        "splitter_type": "law",
                        "source_file": file_path,
                        **chunk.metadata
                    }
                })
            
            return ProcessingResult(
                file_path=file_path,
                splitter_type="law",
                chunks=result_chunks,
                success=True
            )
        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                splitter_type="law",
                chunks=[],
                success=False,
                error_message=str(e)
            )
    
    def process_policy(self, file_path: str) -> ProcessingResult:
        """使用政策公告分割器处理文件"""
        try:
            text_content, tables_info = self.policy_splitter.read_document(file_path)
            chunks = self.policy_splitter.split_text(
                text=text_content,
                tables_info=tables_info,
                file_path=file_path
            )
            
            # 转换为统一格式
            result_chunks = []
            for i, chunk in enumerate(chunks):
                result_chunks.append({
                    "id": i + 1,
                    "content": chunk.content,
                    "metadata": {
                        "splitter_type": "policy",
                        "source_file": file_path,
                        **chunk.metadata
                    }
                })
            
            return ProcessingResult(
                file_path=file_path,
                splitter_type="policy",
                chunks=result_chunks,
                success=True
            )
        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                splitter_type="policy",
                chunks=[],
                success=False,
                error_message=str(e)
            )
    
    def process_qa(self, file_path: str) -> ProcessingResult:
        """使用问答分割器处理文件"""
        try:
            # 创建临时输出文件
            temp_output = os.path.join(self.output_dir, f"temp_qa_{os.path.basename(file_path)}.jsonl")
            
            # 调用QA分割器
            result_code = qa_run(
                input_path=file_path,
                output_path=temp_output,
                preserve_line_breaks=True
            )
            
            if result_code != 0:
                raise ValueError("QA分割器处理失败")
            
            # 读取结果并转换为统一格式
            result_chunks = []
            if os.path.exists(temp_output):
                with open(temp_output, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            result_chunks.append({
                                "id": data["id"],
                                "content": {
                                    "question": data["question"],
                                    "answer": data["answer"]
                                },
                                "metadata": {
                                    "splitter_type": "qa",
                                    "source_file": file_path,
                                    **data["meta"]
                                }
                            })
                
                # 清理临时文件
                os.remove(temp_output)
            
            return ProcessingResult(
                file_path=file_path,
                splitter_type="qa",
                chunks=result_chunks,
                success=True
            )
        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                splitter_type="qa",
                chunks=[],
                success=False,
                error_message=str(e)
            )
    
    def process_file(self, file_path: str) -> ProcessingResult:
        """处理单个文件"""
        if not os.path.exists(file_path):
            return ProcessingResult(
                file_path=file_path,
                splitter_type="unknown",
                chunks=[],
                success=False,
                error_message="文件不存在"
            )
        
        # 检测分割器类型
        splitter_type = self.detect_splitter_by_folder(file_path)
        print(f"使用分割器: {splitter_type} -> {file_path}")
        
        # 调用对应的分割器
        if splitter_type == 'semantic':
            return self.process_semantic(file_path)
        elif splitter_type == 'table':
            return self.process_table(file_path)
        elif splitter_type == 'law':
            return self.process_law(file_path)
        elif splitter_type == 'policy':
            return self.process_policy(file_path)
        elif splitter_type == 'qa':
            return self.process_qa(file_path)
        else:
            return ProcessingResult(
                file_path=file_path,
                splitter_type="unknown",
                chunks=[],
                success=False,
                error_message="未知的分割器类型"
            )
    
    def process_directory(self, directory_path: str, output_file: str = "result.jsonl") -> None:
        """处理目录中的所有文件，并实时写入结果"""
        output_path = os.path.join(self.output_dir, output_file)
        
        print(f"开始遍历目录: {directory_path}")
        print(f"结果将实时写入: {output_path}")
        
        # 清空输出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            pass
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                if file_ext in self.supported_extensions:
                    print(f"处理文件: {file_path}")
                    result = self.process_file(file_path)
                    
                    # 更新统计信息
                    self.stats["total_files"] += 1
                    if result.success:
                        self.stats["successful_files"] += 1
                        self.stats["total_chunks"] += len(result.chunks)
                        print(f"✓ 成功处理: {file_path} ({len(result.chunks)} 个分块)")
                    else:
                        self.stats["failed_files"] += 1
                        print(f"✗ 处理失败: {file_path} - {result.error_message}")
                    
                    # 更新分割器使用统计
                    if result.splitter_type not in self.stats["splitter_usage"]:
                        self.stats["splitter_usage"][result.splitter_type] = 0
                    self.stats["splitter_usage"][result.splitter_type] += 1
                    
                    # 更新文件类型统计
                    if file_ext not in self.stats["file_types"]:
                        self.stats["file_types"][file_ext] = 0
                    self.stats["file_types"][file_ext] += 1
                    
                    # 立即写入结果
                    self._write_result_immediately(result, output_path)
        
        print(f"所有结果已保存到: {output_path}")
    
    def _write_result_immediately(self, result: ProcessingResult, output_path: str) -> None:
        """立即写入单个处理结果到文件"""
        with open(output_path, 'a', encoding='utf-8') as f:
            if result.success:
                for chunk in result.chunks:
                    f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
            else:
                # 记录错误信息
                error_record = {
                    "id": -1,
                    "content": f"处理失败: {result.error_message}",
                    "metadata": {
                        "splitter_type": result.splitter_type,
                        "source_file": result.file_path,
                        "error": True
                    }
                }
                f.write(json.dumps(error_record, ensure_ascii=False) + '\n')
    
    def save_results(self, results: List[ProcessingResult], output_file: str = "result.jsonl"):
        """保存所有结果到统一的JSONL文件（保留向后兼容性）"""
        output_path = os.path.join(self.output_dir, output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                if result.success:
                    for chunk in result.chunks:
                        f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
                else:
                    # 记录错误信息
                    error_record = {
                        "id": -1,
                        "content": f"处理失败: {result.error_message}",
                        "metadata": {
                            "splitter_type": result.splitter_type,
                            "source_file": result.file_path,
                            "error": True
                        }
                    }
                    f.write(json.dumps(error_record, ensure_ascii=False) + '\n')
        
        print(f"所有结果已保存到: {output_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.stats.copy()


def main():
    """主函数 - 示例用法"""
    agent = TextSpilterAgent()
    
    # 处理整个知识库目录
    directory_path = "KnowledgeBase"
    print(f"开始处理目录: {directory_path}")
    
    # 直接处理目录，结果会实时写入文件
    agent.process_directory(directory_path)
    
    # 显示统计信息
    stats = agent.get_statistics()
    print("\n=== 处理统计 ===")
    print(f"总文件数: {stats['total_files']}")
    print(f"成功处理: {stats['successful_files']}")
    print(f"处理失败: {stats['failed_files']}")
    print(f"总分块数: {stats['total_chunks']}")
    print(f"分割器使用情况: {stats['splitter_usage']}")
    print(f"文件类型分布: {stats['file_types']}")


if __name__ == "__main__":
    main()
