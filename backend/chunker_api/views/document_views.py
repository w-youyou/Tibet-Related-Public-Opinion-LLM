import json
import logging
import os
import re
import uuid
from typing import Any, Dict

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..llm_service import get_llm_service
from .Spilter.BasicSpilter import BasicSpilter

logger = logging.getLogger(__name__)


def _ensure_upload_dir() -> str:
    """确保上传目录存在。

    作用：
    - 将用户上传文件统一保存到 backend/media/upload_files 目录，便于后续抽取元数据/分块入库。

    返回值：
    - upload_dir: str，上传目录的绝对路径
    """
    upload_dir = os.path.join(str(settings.MEDIA_ROOT), 'upload_files')
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _guess_title_from_filename(filename: str) -> str:
    """从文件名猜测文档标题。

    参数：
    - filename: 原始文件名

    返回值：
    - title: 去掉扩展名的标题
    """
    return os.path.splitext(filename or '')[0] or '未命名文档'


def _extract_metadata_by_llm(text_preview: str) -> Dict[str, Any]:
    """调用大模型从文本预览中提取结构化元数据（半智能）。

    作用：
    - 通过硬格式 JSON 输出约束，让模型尽量只返回 dept/pub_date/region。

    参数：
    - text_preview: 文档前若干字符，用于抽取关键信息

    返回值：
    - dict: {dept, pub_date, region}，字段缺失时返回空字符串

    实现思路：
    - system_prompt 约束输出为 JSON
    - 对输出做简单 JSON 解析，失败则返回空
    """
    api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
    if not api_key:
        return {"dept": "", "pub_date": "", "region": ""}

    llm = get_llm_service(api_key=api_key, model_name="qwen3-omni-flash")

    sys_prompt = "你是一个信息抽取助手，只能输出JSON。"
    prompt = (
        "请从下面的政务/政策/通知类文本中提取以下字段，并严格输出JSON（不要输出多余文本）：\n"
        "{\"dept\":\"发布部门\",\"pub_date\":\"发布日期(YYYY-MM-DD或YYYY-MM或YYYY)\",\"region\":\"地区\"}\n\n"
        "文本：\n"
        f"{text_preview}\n"
    )

    try:
        raw = llm.generate_answer(prompt, system_prompt=sys_prompt) or ""
        raw = raw.strip()
        # 有些模型会包裹 ```json
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"```$", "", raw).strip()
        data = json.loads(raw)
        return {
            "dept": (data.get("dept") or "").strip(),
            "pub_date": (data.get("pub_date") or "").strip(),
            "region": (data.get("region") or "").strip(),
        }
    except Exception as e:
        logger.warning(f"LLM 元数据抽取失败，将返回空字段: {e}")
        return {"dept": "", "pub_date": "", "region": ""}


@csrf_exempt
@require_http_methods(["POST"])
def upload_and_extract_metadata(request):
    """上传文件并半自动抽取元数据（用于创建知识库流程）。

    作用：
    - 保存文件到 backend/media/upload_files
    - 读取文本预览（前若干字符）
    - 调用 LLM 提取 dept/pub_date/region
    - title 与 effective_status 由程序自动给默认值
    - 返回给前端用于用户确认

    请求参数（multipart/form-data）：
    - file: 上传文件

    返回值（JSON）：
    - success: bool
    - upload: {file_id, file_name, saved_path}
    - metadata: {title, dept, pub_date, region, effective_status}

    实现思路：
    - 文件落盘 -> BasicSpilter.get_file_text 读文本 -> 截取 preview -> LLM 抽取
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)

    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': '没有上传文件'}, status=400)

    upload_dir = _ensure_upload_dir()

    f = request.FILES['file']
    file_ext = os.path.splitext(f.name)[1].lower()

    # 生成唯一文件名，避免冲突
    file_id = uuid.uuid4().hex
    saved_name = f"{file_id}{file_ext}"
    saved_path = os.path.join(upload_dir, saved_name)

    try:
        with open(saved_path, 'wb') as fp:
            for chunk in f.chunks():
                fp.write(chunk)

        # 读取文本预览（对非文本也尽量读）
        preview = ""
        try:
            splitter = BasicSpilter()
            text = splitter.get_file_text(saved_path)
            preview = (text or "").strip()[:5000]
        except Exception as e:
            logger.warning(f"读取文本预览失败(可能是非文本格式或依赖缺失): {e}")
            preview = _guess_title_from_filename(f.name)

        llm_meta = _extract_metadata_by_llm(preview)

        resp = {
            'success': True,
            'upload': {
                'file_id': file_id,
                'file_name': f.name,
                'saved_path': saved_path,
            },
            'metadata': {
                'title': _guess_title_from_filename(f.name),
                'dept': llm_meta.get('dept', ''),
                'pub_date': llm_meta.get('pub_date', ''),
                'region': llm_meta.get('region', ''),
                'effective_status': '有效',
            }
        }
        return JsonResponse(resp)

    except Exception as e:
        logger.error(f"上传并抽取元数据失败: {e}")
        return JsonResponse({'success': False, 'error': f'处理失败: {e}'}, status=500)
