# -*- coding: utf-8 -*-
from typing import List, Tuple
import numpy as np

class AdaptiveThresholdFilter:
    """自适应阈值筛选器"""
    
    @staticmethod
    def find_optimal_threshold(
        scores: List[float], 
        min_docs: int = 3,
        quantile: float = 0.5,
        min_gap_ratio: float = 0.1
    ) -> Tuple[float, List[int]]:
        """
        自适应阈值：分位数 + Gap截断 + 缺证兜底
        """
        if not scores:
            return 0.0, []

        # 先按分数降序排序（返回索引仍映射回原列表）
        indexed_scores = [(i, float(s)) for i, s in enumerate(scores)]
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        scores_array = np.array([s for _, s in indexed_scores], dtype=float)
        
        # 1. 分位数基准
        quantile_threshold = np.quantile(scores_array, quantile)
        
        # 2. Gap截断分析
        gaps = []
        for i in range(1, len(scores_array)):
            gap = scores_array[i-1] - scores_array[i]
            gap_ratio = gap / (scores_array[0] + 1e-8)  # 相对第一个分数的比例
            gaps.append((i, gap, gap_ratio))
        
        # 寻找显著Gap
        gap_threshold_idx = len(scores_array) - 1  # 默认取最后一个
        for idx, gap, gap_ratio in gaps:
            if gap_ratio > min_gap_ratio and idx >= min_docs:
                # idx 表示显著下降发生在 scores[idx-1] -> scores[idx]，阈值取下降前的分数
                gap_threshold_idx = max(0, idx - 1)
                break
        
        gap_threshold = scores_array[gap_threshold_idx] if gap_threshold_idx < len(scores_array) else scores_array[-1]
        
        # 3. 最终阈值：取分位数和Gap阈值的最大值，确保至少min_docs个文档
        final_threshold = max(quantile_threshold, gap_threshold)
        
        # 确保至少保留min_docs个文档
        keep_positions: List[int] = []
        for pos, score in enumerate(scores_array):
            if score >= final_threshold or len(keep_positions) < min_docs:
                keep_positions.append(pos)
            else:
                # 已按分数降序，后续只会更低
                break

        keep_indices = [indexed_scores[pos][0] for pos in keep_positions]
        
        return final_threshold, keep_indices
