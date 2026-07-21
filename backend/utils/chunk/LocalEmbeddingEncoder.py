#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
本地文本编码器
使用 sentence_transformers.SentenceTransformer 加载本地模型（如 bge-large-zh）
"""

import os
from typing import List, Dict, Optional, Union
from chromadb.config import Settings
import chromadb


class _SentenceTransformerEmbeddings:
    """薄封装：让 SentenceTransformer 兼容 LangChain 的 embed_documents / embed_query 接口。

    HuggingFaceBgeEmbeddings（langchain_community）与 PyTorch 2.12 存在兼容性问题
    （Negative indexing is not supported），因此直接用 sentence_transformers 替代。
    """

    def __init__(self, model_path: str, device: str = "cpu"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_path, device=device)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self._model.encode([text], normalize_embeddings=True)[0].tolist()


class LocalEmbeddingEncoder:
    """本地文本编码器"""
    
    _global_hf_embeddings = None # 类级别的单例模型缓存
    
    def __init__(self, 
                 model_path: str,
                 chroma_db_path: str = "./chroma_db",
                 collection_name: Optional[str] = None):
        """
        初始化编码器
        """
        self.model_path = model_path
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        
        # 延迟初始化 HuggingFace Embeddings
        self._hf_embeddings = None
        
        # 初始化 Chroma 客户端
        self._init_chroma_client()
        
        if collection_name:
            self._load_collection(collection_name)
    
    def _init_chroma_client(self):
        os.makedirs(self.chroma_db_path, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.collection = None

    def _load_collection(self, collection_name: str):
        if not collection_name:
            raise ValueError("必须提供集合名称")
        self.collection_name = collection_name
        try:
            self.collection = self.chroma_client.get_collection(
                name=collection_name
            )
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": "Created by LocalEmbeddingEncoder"}
            )
            
    def set_collection(self, collection_name: str):
        self._load_collection(collection_name)
        
    @property
    def hf_embeddings(self):
        if LocalEmbeddingEncoder._global_hf_embeddings is None:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            LocalEmbeddingEncoder._global_hf_embeddings = _SentenceTransformerEmbeddings(
                model_path=self.model_path,
                device=device,
            )
        self._hf_embeddings = LocalEmbeddingEncoder._global_hf_embeddings
        return self._hf_embeddings

    def encode(self, contents: List[Union[str, Dict]]) -> List[Dict]:
        """
        对内容进行向量化编码
        """
        if not contents:
            return []
            
        texts = []
        for item in contents:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                # bge-large 仅支持文本，提取纯文本描述
                if 'text' in item:
                    texts.append(item['text'])
                else:
                    texts.append(str(item))
                    
        try:
            embeddings = self.hf_embeddings.embed_documents(texts)
            results = []
            for i, emb in enumerate(embeddings):
                results.append({
                    'index': i,
                    'embedding': emb,
                    'type': 'text'
                })
            return results
        except Exception as e:
            raise RuntimeError(f"本地编码失败: {str(e)}")

    def encode_chunk(self, chunk: Dict) -> Optional[Dict]:
        content = chunk.get('content', '')
        if not content:
            return None
            
        try:
            embeddings = self.encode([content])
            if embeddings and len(embeddings) > 0:
                return {
                    'embedding': embeddings[0].get('embedding', []),
                    'index': embeddings[0].get('index', 0),
                    'type': chunk.get('modality_type', 'text')
                }
        except Exception as e:
            print(f"编码失败: {e}")
        return None

    def process_and_store(self, chunks: List[Dict], batch_size: int = 10, metadatas: Optional[List[Dict]] = None):
        if self.collection is None:
            raise ValueError("在保存之前，请先使用 set_collection() 设置一个集合")

        if not chunks:
            return
            
        encoded_chunks = []
        for i, chunk in enumerate(chunks):
            result = self.encode_chunk(chunk)
            if result:
                encoded_chunks.append({
                    'chunk': chunk,
                    'embedding': result['embedding']
                })
            else:
                encoded_chunks.append({
                    'chunk': chunk,
                    'embedding': [0.0] * 1024 # bge-large-zh 输出维度为1024
                })
                
        ids = []
        embeddings = []
        documents = []
        metadata_list = []
        
        for i, item in enumerate(encoded_chunks):
            chunk = item.get('chunk', {})
            embedding = item.get('embedding')
            
            chunk_id = chunk.get('id', i)
            version_id = chunk.get('metadata', {}).get('version_id', '')
            version_str = f"_v{version_id}" if version_id else ""
            doc_id = f"{chunk.get('metadata', {}).get('file_name', 'unknown')}{version_str}_chunk_{chunk_id}"
            ids.append(doc_id)
            embeddings.append(embedding)
            
            if chunk.get('modality_type') == 'text':
                documents.append(chunk.get('content', ''))
            else:
                documents.append(f"[{chunk.get('modality_type')}] {chunk.get('metadata', {}).get('file_name', '')}")
                
            meta = chunk.get('metadata', {}).copy()
            meta['chunk_id'] = chunk_id
            meta['modality_type'] = chunk.get('modality_type', 'text')
            meta['is_active'] = True
            
            # 清理元数据（只能是str, int, float, bool）
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                elif v is None:
                    clean_meta[k] = ""
                else:
                    clean_meta[k] = str(v)
            metadata_list.append(clean_meta)
            
        # 批量存入 ChromaDB
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_embeddings = embeddings[i:i+batch_size]
            batch_documents = documents[i:i+batch_size]
            batch_metadatas = metadata_list[i:i+batch_size]
            
            try:
                self.collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
            except Exception as e:
                print(f"存储批次到 ChromaDB 失败: {e}")

    def query(self, query_text: str, n_results: int = 5, where: Optional[Dict] = None) -> Dict:
        if self.collection is None:
            raise ValueError("在查询之前，请先使用 set_collection() 设置一个集合")
            
        try:
            query_embedding = self.hf_embeddings.embed_query(query_text)
            
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": n_results
            }
            if where:
                query_params["where"] = where
                
            results = self.collection.query(**query_params)
            
            formatted_results = []
            if results.get('ids') and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'distance': results['distances'][0][i] if results.get('distances') else 0.0,
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                        'content': results['documents'][0][i] if results.get('documents') else ""
                    }
                    formatted_results.append(result)
            return formatted_results
        except Exception as e:
            raise RuntimeError(f"查询失败: {str(e)}")
