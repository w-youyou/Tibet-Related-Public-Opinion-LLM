# -*- coding: utf-8 -*-
from typing import List
import numpy as np
from .types import Candidate

class MMRDiversityReranker:
    """MMR多样性重排器"""
    
    def __init__(self, embeddings, lambda_param: float = 0.7):
        self.embeddings = embeddings
        self.lambda_param = lambda_param
    
    def compute_mmr_scores(self, query: str, candidates: List[Candidate], top_k: int) -> List[Candidate]:
        if len(candidates) <= top_k:
            for cand in candidates:
                cand.mmr_score = cand.s_ce_norm
            return candidates
        
        # 嵌入获取
        try:
            query_embedding = np.array(self.embeddings.embed_query(query))
        except Exception as e:
            # 回退到CE分数排序
            sorted_cands = sorted(candidates, key=lambda x: x.s_ce_norm, reverse=True)[:top_k]
            for cand in sorted_cands:
                cand.mmr_score = cand.s_ce_norm
            return sorted_cands
        
        # 文档嵌入获取
        doc_embeddings = []
        valid_candidates = []
        
        for cand in candidates:
            try:
                content = cand.doc.page_content or ""
                if len(content.strip()) > 50:  # 确保内容足够长
                    doc_embedding = np.array(self.embeddings.embed_documents([content])[0])
                    doc_embeddings.append(doc_embedding)
                    valid_candidates.append(cand)
            except Exception as e:
                continue
        
        if len(valid_candidates) <= top_k:
            for cand in valid_candidates:
                cand.mmr_score = cand.s_ce_norm
            return valid_candidates
        
        # MMR算法
        selected = []
        remaining = list(range(len(valid_candidates)))
        
        # 按CE分数选择第一个
        first_idx = max(remaining, key=lambda i: valid_candidates[i].s_ce_norm)
        selected.append(first_idx)
        remaining.remove(first_idx)
        valid_candidates[first_idx].mmr_score = valid_candidates[first_idx].s_ce_norm
        
        while len(selected) < min(top_k, len(valid_candidates)) and remaining:
            best_score = -float('inf')
            best_idx = -1
            
            for idx in remaining:
                relevance = valid_candidates[idx].s_ce_norm
                
                # 相似度计算
                max_similarity = 0.0
                for sel_idx in selected:
                    try:
                        vec1 = doc_embeddings[idx]
                        vec2 = doc_embeddings[sel_idx]
                        # 确保向量归一化
                        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-8)
                        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-8)
                        similarity = np.dot(vec1_norm, vec2_norm)
                        max_similarity = max(max_similarity, similarity)
                    except:
                        continue
                
                # MMR分数计算
                mmr_score = np.clip(
                    self.lambda_param * relevance - (1 - self.lambda_param) * max_similarity, 
                    0.0, 1.0
                )
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx != -1:
                selected.append(best_idx)
                remaining.remove(best_idx)
                valid_candidates[best_idx].mmr_score = best_score
            else:
                break
        
        result = [valid_candidates[i] for i in selected]
        
        # 确保所有候选都有合理的MMR分数
        for cand in result:
            if not hasattr(cand, 'mmr_score') or cand.mmr_score < 0:
                cand.mmr_score = cand.s_ce_norm
        
        return result