#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多模态编码器
使用阿里云百炼 MultiModalEmbedding API 生成向量嵌入，并存储到 Chroma 数据库

功能：
- 支持文本、图片、视频等多种模态的向量化
- 将嵌入向量存储到 Chroma 向量数据库
- 支持批量处理和查询
"""

import os
import json
import shutil
import time
from typing import List, Dict, Optional, Union, Any
from pathlib import Path

try:
    import dashscope
    from dashscope import MultiModalEmbedding
    from http import HTTPStatus
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    print("警告：dashscope 未安装，请运行: pip install dashscope")

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("警告：chromadb 未安装，请运行: pip install chromadb")


class MultimodalEncoder:
    """多模态编码器"""

    _chroma_rebuild_done_for_path = set()
    _chroma_redirect_map = {}
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "tongyi-embedding-vision-plus",
                 chroma_db_path: str = "./chroma_db",
                 collection_name: Optional[str] = None):
        """
        初始化多模态编码器
        
        Args:
            api_key: 阿里云百炼 API Key，如果不提供则从环境变量 DASHSCOPE_API_KEY 读取
            model: 使用的模型名称，默认 tongyi-embedding-vision-plus
            chroma_db_path: Chroma 数据库路径
            collection_name: Chroma 集合名称（可选，可以稍后通过 set_collection 设置）
        """
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("需要安装 dashscope: pip install dashscope")
        
        if not CHROMADB_AVAILABLE:
            raise ImportError("需要安装 chromadb: pip install chromadb")
        
        # 设置 API Key
        if api_key:
            dashscope.api_key = api_key
        elif os.getenv("DASHSCOPE_API_KEY"):
            dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
        else:
            raise ValueError("请提供 API Key 或设置环境变量 DASHSCOPE_API_KEY")
        
        self.model = model
        base_path = os.path.abspath(chroma_db_path)
        # 若该旧路径已被判定损坏并重定向，则后续实例直接走新目录
        self.chroma_db_path = self._chroma_redirect_map.get(base_path, base_path)
        self.collection_name = collection_name
        
        # 初始化 Chroma 客户端
        self._init_chroma_client()
        
        # 如果提供了集合名称，则初始化集合
        if collection_name:
            self._load_collection(collection_name)
    
    def _init_chroma_client(self):
        """初始化 Chroma 客户端"""
        os.makedirs(self.chroma_db_path, exist_ok=True)
        
        # 创建 Chroma 客户端
        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.collection = None # 集合在需要时加载

    def _try_rebuild_chroma(self, error: Exception) -> bool:
        """遇到旧版 Chroma schema 报错时，切换到全新目录重建数据库。"""
        msg = str(error)
        if "collections.topic" not in msg:
            return False

        old_path = self.chroma_db_path
        # 每个旧路径只处理一次，避免重复切目录
        if old_path in self._chroma_rebuild_done_for_path:
            return False
        self._chroma_rebuild_done_for_path.add(old_path)

        try:
            print(f"检测到旧版 Chroma schema，原目录不可用: {old_path}")

            # 先关闭旧客户端引用，降低 Windows 文件占用概率
            try:
                self.collection = None
                self.chroma_client = None
            except Exception:
                pass

            # 关键策略：切到稳定运行目录（避免每次重建都生成新目录）
            fallback_path = os.path.join(os.path.dirname(old_path), "chroma_db_runtime")
            os.makedirs(fallback_path, exist_ok=True)
            self.chroma_db_path = os.path.abspath(fallback_path)
            # 记录重定向：后续新建的 encoder 遇到 old_path 时直接转到 fallback_path
            self._chroma_redirect_map[old_path] = self.chroma_db_path
            print(f"切换到运行中的 Chroma 目录: {self.chroma_db_path}")
            self._init_chroma_client()

            # 尝试异步/尽力清理旧目录（失败不影响主流程）
            try:
                for item in os.listdir(old_path):
                    full = os.path.join(old_path, item)
                    if os.path.isdir(full):
                        shutil.rmtree(full, ignore_errors=True)
                    else:
                        try:
                            os.remove(full)
                        except Exception:
                            pass
            except Exception:
                pass

            return True
        except Exception as rebuild_err:
            print(f"自动重建 Chroma 失败: {rebuild_err}")
            return False

    def _load_collection(self, collection_name: str):
        """加载或创建指定的集合"""
        if not collection_name:
            raise ValueError("必须提供集合名称")
        
        self.collection_name = collection_name
        try:
            self.collection = self.chroma_client.get_collection(
                name=self.collection_name
            )
        except Exception as e:
            rebuilt = self._try_rebuild_chroma(e)
            if rebuilt:
                try:
                    self.collection = self.chroma_client.get_collection(name=self.collection_name)
                    return
                except Exception:
                    pass
            # 集合不存在，创建新集合
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": f"多模态文档嵌入向量集合 - {collection_name}"}
            )

    def set_collection(self, collection_name: str):
        """
        动态设置当前要操作的集合
        
        Args:
            collection_name: 集合名称
        """
        self._load_collection(collection_name)
    
    def _prepare_input(self, content: str, modality_type: str) -> Dict[str, Any]:
        """
        准备输入内容
        
        Args:
            content: 内容（文本、图片Base64或视频URL）
            modality_type: 模态类型 ('text', 'image', 'video')
            
        Returns:
            格式化的输入字典
        """
        if modality_type == 'text':
            # 文本需要包装在 {'text': ...} 字典中
            return {'text': content}
        elif modality_type == 'image':
            # 图片可以是URL或Base64格式
            if content.startswith('http://') or content.startswith('https://'):
                return {'image': content}
            elif content.startswith('data:image'):
                return {'image': content}
            elif content.startswith('/api/media/'):
                # 相对URL，需要转换为完整URL（但这里不转换，由调用者负责）
                # 或者尝试从本地文件系统读取
                raise ValueError("图片相对URL需要先转换为完整URL或Base64格式")
            else:
                # 假设是文件路径，需要转换为Base64
                raise ValueError("图片路径需要先转换为Base64格式或完整URL")
        elif modality_type == 'video':
            # 视频必须是URL
            if content.startswith('http://') or content.startswith('https://'):
                return {'video': content}
            else:
                raise ValueError("视频必须是公开可访问的URL")
        else:
            raise ValueError(f"不支持的模态类型: {modality_type}")
    
    def encode(self, 
               contents: List[Union[str, Dict]], 
               parameters: Optional[Dict] = None) -> List[Dict]:
        """
        对内容进行向量化编码
        
        Args:
            contents: 内容列表，每个元素可以是字符串（文本）或字典（图片/视频）
            parameters: 可选参数（dimension, output_type, fps等）
            
        Returns:
            包含嵌入向量的结果列表
        """
        if not contents:
            return []
        
        # 准备请求参数
        # 确保每个输入项都符合API要求的格式，特别是文本需要包装
        formatted_input = []
        for item in contents:
            if isinstance(item, str):
                # 如果是纯文本字符串，包装成 {'text': ...}
                formatted_input.append({'text': item})
            elif isinstance(item, dict):
                # 如果已经是字典（如 {'image': ...}），直接使用
                formatted_input.append(item)

        request_params = {
            "model": self.model,
            "input": formatted_input
        }
        
        if parameters:
            request_params["parameters"] = parameters
        
        # 调用 API
        try:
            print(f"--- 编码 API 调用 ---")
            print(f"模型: {self.model}")
            print(f"输入内容 (前100字符): {str(contents)[:100]}...")
            
            resp = MultiModalEmbedding.call(**request_params)
            
            if resp.status_code == HTTPStatus.OK:
                embeddings = resp.output.get('embeddings', [])
                return embeddings
            else:
                error_msg = f"API调用失败: {resp.code} - {resp.message}"
                print(f"❌ 编码失败: {error_msg}")
                print(f"请求参数: {json.dumps(request_params, ensure_ascii=False, indent=2)}")
                raise RuntimeError(error_msg)
        
        except Exception as e:
            raise RuntimeError(f"编码失败: {str(e)}")
    
    def encode_chunk(self, chunk: Dict) -> Optional[Dict]:
        """
        对单个分块进行编码
        
        Args:
            chunk: 分块字典，包含 content 和 modality_type
            
        Returns:
            编码结果，包含 embedding 向量
        """
        content = chunk.get('content', '')
        modality_type = chunk.get('modality_type', 'text')
        
        if not content:
            return None
        
        # 准备输入
        try:
            input_item = self._prepare_input(content, modality_type)
            if isinstance(input_item, str):
                # 文本直接传入
                input_list = [input_item]
            else:
                # 图片或视频传入字典
                input_list = [input_item]
        except Exception as e:
            print(f"警告：无法处理内容: {e}")
            return None
        
        # 编码
        try:
            embeddings = self.encode(input_list)
            if embeddings and len(embeddings) > 0:
                return {
                    'embedding': embeddings[0].get('embedding', []),
                    'index': embeddings[0].get('index', 0),
                    'type': embeddings[0].get('type', modality_type)
                }
        except Exception as e:
            print(f"编码失败: {e}")
            return None
        
        return None
    
    def batch_encode(self, chunks: List[Dict], batch_size: int = 10) -> List[Dict]:
        """
        批量编码分块
        
        Args:
            chunks: 分块列表
            batch_size: 批次大小
            
        Returns:
            编码结果列表
        """
        results = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # 准备批量输入
            batch_inputs = []
            for chunk in batch:
                content = chunk.get('content', '')
                modality_type = chunk.get('modality_type', 'text')
                try:
                    input_item = self._prepare_input(content, modality_type)
                    if isinstance(input_item, str):
                        batch_inputs.append(input_item)
                    else:
                        batch_inputs.append(input_item)
                except Exception as e:
                    print(f"警告：跳过无法处理的内容: {e}")
                    batch_inputs.append(None)
            
            # 过滤掉 None
            valid_inputs = [inp for inp in batch_inputs if inp is not None]
            if not valid_inputs:
                continue
            
            # 批量编码
            try:
                embeddings = self.encode(valid_inputs)
                
                # 匹配结果到原始分块
                valid_idx = 0
                for j, chunk in enumerate(batch):
                    if batch_inputs[j] is not None:
                        if valid_idx < len(embeddings):
                            result = {
                                'chunk': chunk,
                                'embedding': embeddings[valid_idx].get('embedding', []),
                                'index': embeddings[valid_idx].get('index', valid_idx),
                                'type': embeddings[valid_idx].get('type', chunk.get('modality_type', 'text'))
                            }
                            results.append(result)
                            valid_idx += 1
                        else:
                            print(f"警告：编码结果数量不匹配")
                    else:
                        results.append({'chunk': chunk, 'embedding': None, 'error': '预处理失败'})
            
            except Exception as e:
                print(f"批量编码失败: {e}")
                # 为失败的批次添加错误信息
                for chunk in batch:
                    results.append({'chunk': chunk, 'embedding': None, 'error': str(e)})
        
        return results
    
    def save_to_chroma(self, 
                      encoded_chunks: List[Dict],
                      metadatas: Optional[List[Dict]] = None):
        """
        将编码后的分块保存到 Chroma 数据库
        
        Args:
            encoded_chunks: 编码结果列表，每个元素包含 'chunk' 和 'embedding'
            metadatas: 可选的元数据列表
        """
        if self.collection is None:
            raise ValueError("在保存之前，请先使用 set_collection() 设置一个集合")

        if not encoded_chunks:
            return
        
        # 准备数据
        ids = []
        embeddings = []
        documents = []
        metadata_list = []
        
        for i, item in enumerate(encoded_chunks):
            if item.get('embedding') is None:
                continue
            
            chunk = item.get('chunk', {})
            embedding = item.get('embedding')
            
            # 生成唯一ID
            chunk_id = chunk.get('id', i)
            doc_id = f"{chunk.get('metadata', {}).get('file_name', 'unknown')}_chunk_{chunk_id}"
            ids.append(doc_id)
            
            # 嵌入向量
            embeddings.append(embedding)
            
            # 文档内容（文本或描述）
            if chunk.get('modality_type') == 'text':
                documents.append(chunk.get('content', ''))
            else:
                # 对于图片和视频，使用描述
                documents.append(f"[{chunk.get('modality_type')}] {chunk.get('metadata', {}).get('file_name', '')}")
            
            # 元数据
            metadata = chunk.get('metadata', {}).copy()
            metadata['modality_type'] = chunk.get('modality_type', 'text')
            metadata['chunk_id'] = chunk_id
            
            if metadatas and i < len(metadatas):
                metadata.update(metadatas[i])
            
            metadata_list.append(metadata)
        
        # 添加到 Chroma 集合
        if ids:
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadata_list
                )
                print(f"成功保存 {len(ids)} 个向量到 Chroma 数据库")
            except Exception as e:
                rebuilt = self._try_rebuild_chroma(e)
                if rebuilt:
                    # 重建后重建集合并重试一次
                    self._load_collection(self.collection_name)
                    self.collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadata_list
                    )
                    print(f"重建后成功保存 {len(ids)} 个向量到 Chroma 数据库")
                    return
                print(f"保存到 Chroma 失败: {e}")
                raise
    
    def process_and_store(self, 
                         chunks: List[Dict],
                         batch_size: int = 10,
                         metadatas: Optional[List[Dict]] = None):
        """
        处理分块并存储到 Chroma（完整流程）
        
        Args:
            chunks: 分块列表
            batch_size: 批次大小
            metadatas: 可选的元数据列表
        """
        print(f"开始处理 {len(chunks)} 个分块...")
        
        # 批量编码
        encoded_chunks = self.batch_encode(chunks, batch_size=batch_size)
        print(f"编码完成，成功编码 {sum(1 for e in encoded_chunks if e.get('embedding'))} 个分块")
        
        # 保存到 Chroma
        self.save_to_chroma(encoded_chunks, metadatas)
    
    def query(self, 
              query_text: str,
              n_results: int = 5,
              modality_filter: Optional[str] = None,
              where: Optional[Dict] = None) -> List[Dict]:
        """
        查询相似向量
        
        Args:
            query_text: 查询文本
            n_results: 返回结果数量
            modality_filter: 可选的模态类型过滤
            where: 可选的元数据过滤条件
            
        Returns:
            查询结果列表
        """
        if self.collection is None:
            raise ValueError("在查询之前，请先使用 set_collection() 设置一个集合")

        # 首先对查询文本进行编码
        try:
            # print(f"\n🔍 查询文本: {query_text}")  # 可按需打开调试输出
            query_embeddings = self.encode([query_text])
            if not query_embeddings:
                return []
            
            query_embedding = query_embeddings[0].get('embedding')
            print(f"✅ 查询文本编码成功，向量维度: {len(query_embedding)}")
        except Exception as e:
            print(f"❌ 查询编码失败: {e}")
            return []
        
        # 准备查询过滤器
        final_where = where.copy() if where else {}
        if modality_filter:
            final_where["modality_type"] = modality_filter
        
        # 在 Chroma 中查询
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=final_where if final_where else None
            )
            
            # 格式化结果
            formatted_results = []
            if results.get('ids') and len(results['ids'][0]) > 0:
                print(f"📚 检索到 {len(results['ids'][0])} 条相关内容:")
                for i in range(len(results['ids'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None,
                        'document': results['documents'][0][i] if 'documents' in results else None,
                        'metadata': results['metadatas'][0][i] if 'metadatas' in results else None
                    }
                    formatted_results.append(result)
                    
                    # 打印检索结果
                    print(f"\n  [{i+1}] 相似度: {1 - result['distance']:.4f}")
                    print(f"      文档ID: {result['id']}")
                    print(f"      内容: {result['document']}")
                    if result['metadata']:
                        print(f"      元数据: {result['metadata']}")
            else:
                print(f"⚠️ 未检索到相关内容")
            
            return formatted_results
        
        except Exception as e:
            rebuilt = self._try_rebuild_chroma(e)
            if rebuilt:
                try:
                    self._load_collection(self.collection_name)
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=n_results,
                        where=final_where if final_where else None
                    )
                    formatted_results = []
                    if results.get('ids') and len(results['ids'][0]) > 0:
                        for i in range(len(results['ids'][0])):
                            formatted_results.append({
                                'id': results['ids'][0][i],
                                'distance': results['distances'][0][i] if 'distances' in results else None,
                                'document': results['documents'][0][i] if 'documents' in results else None,
                                'metadata': results['metadatas'][0][i] if 'metadatas' in results else None
                            })
                    return formatted_results
                except Exception as retry_err:
                    print(f"重建后查询失败: {retry_err}")
            print(f"❌ 查询失败: {e}")
            return []


def main():
    """测试示例"""
    # 需要设置 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("请设置环境变量 DASHSCOPE_API_KEY")
        return
    
    # 初始化编码器
    encoder = MultimodalEncoder(
        api_key=api_key,
        model="tongyi-embedding-vision-plus",
        chroma_db_path="./chroma_db",
        collection_name="test_multimodal"
    )
    
    # 测试文本编码
    test_chunks = [
        {
            'id': 1,
            'content': '这是一个测试文本块',
            'modality_type': 'text',
            'metadata': {'file_name': 'test.txt', 'chunk_index': 1}
        },
        {
            'id': 2,
            'content': '这是另一个测试文本块',
            'modality_type': 'text',
            'metadata': {'file_name': 'test.txt', 'chunk_index': 2}
        }
    ]
    
    # 处理并存储
    encoder.process_and_store(test_chunks)
    
    # 测试查询
    results = encoder.query("测试", n_results=2)
    print(f"查询结果: {results}")


if __name__ == "__main__":
    main()

