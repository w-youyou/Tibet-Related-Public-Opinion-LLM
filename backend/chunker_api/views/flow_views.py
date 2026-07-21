import json
import logging
import os
import tempfile

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..flow import extract_and_render_flow, extract_flow_from_text

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def flow_extract_text(request):
    try:
        data = json.loads(request.body or "{}")
        text = (data.get("text") or "").strip()
        title = data.get("title") or "政务流程"
        source_file = data.get("source_file")
        use_agent = bool(data.get("use_agent", True))
        if not text:
            return JsonResponse({"success": False, "error": "text不能为空"}, status=400)

        graph = extract_flow_from_text(text=text, title=title, source_file=source_file, use_agent=use_agent)
        return JsonResponse({"success": True, "flow_graph": graph.to_dict()})
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "无效JSON"}, status=400)
    except Exception as e:
        logger.error(f"flow_extract_text failed: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def flow_auto_from_file(request):
    temp_file_path = None
    try:
        title = None
        use_agent = True

        if 'file' in request.FILES:
            up = request.FILES['file']
            title = request.POST.get('title') or up.name
            use_agent = request.POST.get('use_agent', 'true').lower() != 'false'

            suffix = os.path.splitext(up.name)[1] or '.txt'
            tmp_dir = getattr(settings, 'TMP_DIR', os.path.join(settings.BASE_DIR, 'tmp'))
            os.makedirs(tmp_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tmp_dir) as tf:
                for chunk in up.chunks():
                    tf.write(chunk)
                temp_file_path = tf.name
            file_path = temp_file_path
        else:
            data = json.loads(request.body or "{}")
            file_path = (data.get("file_path") or "").strip()
            title = data.get("title")
            use_agent = bool(data.get("use_agent", True))
            if not file_path:
                return JsonResponse({"success": False, "error": "file_path不能为空或请上传file"}, status=400)

        result = extract_and_render_flow(file_path=file_path, title=title, use_agent=use_agent, request=request)
        return JsonResponse({"success": True, **result})
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "无效JSON"}, status=400)
    except FileNotFoundError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=404)
    except Exception as e:
        logger.error(f"flow_auto_from_file failed: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass


@require_http_methods(["GET"])
def serve_flow_media(request, file_name: str):
    try:
        base_dir = os.path.join(settings.MEDIA_ROOT, "flow_diagrams")
        full_path = os.path.normpath(os.path.join(base_dir, file_name))
        if not full_path.startswith(os.path.normpath(base_dir)):
            raise Http404("非法路径")
        if not os.path.exists(full_path):
            raise Http404("文件不存在")
        return FileResponse(open(full_path, "rb"), as_attachment=False)
    except Http404:
        raise
    except Exception as e:
        logger.error(f"serve_flow_media failed: {e}")
        raise Http404("无法读取流程图文件")
