# -*- coding: utf-8 -*-
"""
Timeline views — 舆情时间线数据提取 API。

从知识库文档中提取带有时间信息的事件，返回结构化的时间线数据。
"""

import json
import re
import logging
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from ..models import KnowledgeBase

logger = logging.getLogger(__name__)

# 日期正则模式
DATE_PATTERNS = [
    # 2024年3月15日 / 2024-03-15 / 2024/03/15
    (r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日]?', '%Y-%m-%d'),
    # 2024年3月 / 2024-03
    (r'(\d{4})[年\-/](\d{1,2})月?', '%Y-%m'),
    # 2024年
    (r'(\d{4})年', '%Y'),
    # 藏历纪年（如：藏历木龙年）— 简化处理
    (r'藏历[\u0F00-\uFFF\w]+年', None),
]

# 事件关键词
EVENT_KEYWORDS = [
    '事件', '发生', '爆发', '宣布', '发布', '召开', '举行',
    '签署', '通过', '实施', '生效', '成立', '建立',
    '抗议', '示威', '冲突', '事故', '灾害',
]


def _extract_dates_from_text(text: str) -> list:
    """从文本中提取日期信息。"""
    dates = []
    for pattern, fmt in DATE_PATTERNS:
        matches = re.finditer(pattern, text)
        for match in matches:
            date_str = match.group(0)
            try:
                if fmt:
                    # 提取年月日部分
                    groups = match.groups()
                    if len(groups) >= 3:
                        parsed = datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                    elif len(groups) >= 2:
                        parsed = datetime(int(groups[0]), int(groups[1]), 1)
                    else:
                        parsed = datetime(int(groups[0]), 1, 1)
                    dates.append({
                        'date_str': date_str,
                        'date': parsed.strftime('%Y-%m-%d'),
                        'year': parsed.year,
                        'month': parsed.month if len(groups) >= 2 else None,
                        'day': parsed.day if len(groups) >= 3 else None,
                    })
                else:
                    # 藏历等特殊日期
                    dates.append({
                        'date_str': date_str,
                        'date': None,
                        'year': None,
                    })
            except (ValueError, IndexError):
                dates.append({
                    'date_str': date_str,
                    'date': None,
                    'year': None,
                })
    return dates


def _extract_event_context(text: str, date_match: re.Match, context_chars: int = 100) -> str:
    """提取日期周围的事件上下文。"""
    start = max(0, date_match.start() - context_chars)
    end = min(len(text), date_match.end() + context_chars)
    context = text[start:end].strip()
    # 清理换行和多余空格
    context = re.sub(r'\s+', ' ', context)
    return context


def _is_event_related(text: str) -> bool:
    """判断文本是否与事件相关。"""
    return any(kw in text for kw in EVENT_KEYWORDS)


@csrf_exempt
@require_http_methods(["POST"])
def extract_timeline(request):
    """从知识库中提取时间线数据。
    
    请求参数:
    - knowledge_base_id: 知识库ID（必填）
    - query: 搜索关键词（可选，用于过滤相关文档）
    - year_range: 年份范围 [start_year, end_year]（可选）
    
    返回:
    - events: 时间线事件列表，每个事件包含 date, title, description, source
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body or '{}')
        kb_id = data.get('knowledge_base_id')
        query = (data.get('query') or '').strip()
        year_range = data.get('year_range')
        
        if not kb_id:
            return JsonResponse({'success': False, 'error': '请指定知识库'}, status=400)
        
        # 获取知识库
        try:
            kb = KnowledgeBase.objects.get(id=kb_id, user=request.user)
        except KnowledgeBase.DoesNotExist:
            return JsonResponse({'success': False, 'error': '知识库不存在或无权限'}, status=404)
        
        # 从 ChromaDB 获取文档
        from ..rag import get_rag_service
        api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
        if not api_key:
            return JsonResponse({'success': False, 'error': '未配置 API Key'}, status=500)
        
        chroma_path = getattr(settings, 'CHROMA_DB_PATH', './chroma_db')
        rag = get_rag_service(api_key=api_key, chroma_db_path=chroma_path)
        
        # 获取集合中的所有文档
        store = rag.retriever.get_chroma(kb.collection_name)
        raw = store._collection.get(include=["documents", "metadatas"])
        
        events = []
        documents = raw.get('documents', []) or []
        metadatas = raw.get('metadatas', []) or []
        
        for doc_content, meta in zip(documents, metadatas):
            if not doc_content:
                continue
            
            # 如果有搜索关键词，先过滤
            if query and query.lower() not in doc_content.lower():
                continue
            
            # 提取日期
            dates = _extract_dates_from_text(doc_content)
            if not dates:
                continue
            
            # 过滤年份范围
            if year_range and len(year_range) == 2:
                start_year, end_year = year_range
                dates = [d for d in dates if d.get('year') and start_year <= d['year'] <= end_year]
            
            for date_info in dates:
                # 提取事件上下文
                context = doc_content[:200]  # 取前200字符作为描述
                if len(doc_content) > 200:
                    context += '...'
                
                # 判断是否是事件相关内容
                is_event = _is_event_related(doc_content)
                
                event = {
                    'date': date_info.get('date'),
                    'date_str': date_info.get('date_str'),
                    'year': date_info.get('year'),
                    'title': context[:50] + ('...' if len(context) > 50 else ''),
                    'description': context,
                    'source_file': meta.get('file_name') or meta.get('source') or '未知',
                    'chunk_id': meta.get('chunk_id'),
                    'is_event': is_event,
                    'relevance_score': 1.0 if is_event else 0.5,
                }
                events.append(event)
        
        # 按日期排序
        events.sort(key=lambda x: x.get('date') or '9999-99-99')
        
        # 去重（相同日期和相似描述的合并）
        seen = set()
        unique_events = []
        for e in events:
            key = (e.get('date'), e.get('title', '')[:30])
            if key not in seen:
                seen.add(key)
                unique_events.append(e)
        
        # 统计信息
        years = [e['year'] for e in unique_events if e.get('year')]
        stats = {
            'total_events': len(unique_events),
            'event_count': sum(1 for e in unique_events if e.get('is_event')),
            'year_range': [min(years), max(years)] if years else None,
        }
        
        return JsonResponse({
            'success': True,
            'events': unique_events[:100],  # 限制返回数量
            'stats': stats,
            'knowledge_base': {
                'id': kb.id,
                'name': kb.name,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的 JSON'}, status=400)
    except Exception as e:
        logger.error(f"extract_timeline failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def timeline_stats(request):
    """获取时间线统计信息（不需要具体知识库）。"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)
    
    try:
        # 获取用户的所有知识库
        user_kbs = KnowledgeBase.objects.filter(user=request.user, status='active')
        
        return JsonResponse({
            'success': True,
            'knowledge_bases': [
                {'id': kb.id, 'name': kb.name}
                for kb in user_kbs
            ]
        })
    except Exception as e:
        logger.error(f"timeline_stats failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)