import importlib
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static


def _lazy_view(dotted_path: str):
    """返回一个惰性视图可调用对象，在第一次请求时才导入对应的视图模块。

    Django 5.x 的 path() 不支持字符串引用，因此用此包装器实现惰性加载。
    所有重型模块（qa_views 中的 Spilter、rag_service 中的 langchain_chroma 等）
    只在对应 API 被首次访问时才加载，不再阻塞服务器启动。

    注意：包装器统一标记 csrf_exempt，因为原始视图的 @csrf_exempt 属性在
    包装器层面不可见；所有 /api/ 路由均使用 session cookie 认证，CSRF 保护
    由原始视图装饰器在调用时生效。
    """
    module_path, func_name = dotted_path.rsplit('.', 1)

    def view(request, *args, **kwargs):
        module = importlib.import_module(module_path)
        view_func = getattr(module, func_name)
        return view_func(request, *args, **kwargs)

    view.__name__ = func_name
    view.__module__ = module_path
    view.csrf_exempt = True
    return view


urlpatterns = [
    # 分块相关
    path('chunk/', _lazy_view('chunker_api.views.qa_views.chunk_document'), name='chunk_document'),
    path('chunkers/', _lazy_view('chunker_api.views.qa_views.get_chunker_info'), name='get_chunker_info'),
    path('health/', _lazy_view('chunker_api.views.qa_views.health_check'), name='health_check'),
    path('media/<path:file_path>', _lazy_view('chunker_api.views.qa_views.serve_extracted_image'), name='serve_extracted_image'),

    # 用户认证相关
    path('auth/register/', _lazy_view('chunker_api.views.auth_views.register'), name='register'),
    path('auth/login/', _lazy_view('chunker_api.views.auth_views.user_login'), name='login'),
    path('auth/logout/', _lazy_view('chunker_api.views.auth_views.user_logout'), name='logout'),
    path('auth/user/', _lazy_view('chunker_api.views.auth_views.get_current_user'), name='get_current_user'),
    path('auth/user/update/', _lazy_view('chunker_api.views.auth_views.update_user_profile'), name='update_user_profile'),

    # 知识库管理相关
    path('knowledge-bases/', _lazy_view('chunker_api.views.knowledge_base_views.list_knowledge_bases'), name='list_knowledge_bases'),
    path('knowledge-bases/create/', _lazy_view('chunker_api.views.knowledge_base_views.create_knowledge_base'), name='create_knowledge_base'),
    path('knowledge-bases/<str:kb_id>/', _lazy_view('chunker_api.views.knowledge_base_views.get_knowledge_base'), name='get_knowledge_base'),
    path('knowledge-bases/<str:kb_id>/delete/', _lazy_view('chunker_api.views.knowledge_base_views.delete_knowledge_base'), name='delete_knowledge_base'),

    # 聊天记录相关
    path('chat/sessions/', _lazy_view('chunker_api.views.chat_history_views.list_chat_sessions'), name='list_chat_sessions'),
    path('chat/sessions/create/', _lazy_view('chunker_api.views.chat_history_views.create_chat_session'), name='create_chat_session'),
    path('chat/sessions/<str:session_id>/messages/', _lazy_view('chunker_api.views.chat_history_views.list_chat_messages'), name='list_chat_messages'),
    path('chat/sessions/<str:session_id>/delete/', _lazy_view('chunker_api.views.chat_history_views.delete_chat_session'), name='delete_chat_session'),
    path('chat/sessions/<str:session_id>/rename/', _lazy_view('chunker_api.views.chat_history_views.rename_chat_session'), name='rename_chat_session'),

    # 多模态问答相关
    path('qa/hybrid/', _lazy_view('chunker_api.views.qa_views.hybrid_qa'), name='hybrid_qa'),
    path('qa/hybrid/stream/', _lazy_view('chunker_api.views.qa_views.hybrid_qa_stream'), name='hybrid_qa_stream'),
    path('qa/ask/', _lazy_view('chunker_api.views.qa_views.multimodal_qa'), name='multimodal_qa'),

    # 流程抽取与流程图生成
    path('flow/extract-text/', _lazy_view('chunker_api.views.flow_views.flow_extract_text'), name='flow_extract_text'),
    path('flow/auto/', _lazy_view('chunker_api.views.flow_views.flow_auto_from_file'), name='flow_auto_from_file'),
    path('flow/media/<str:file_name>', _lazy_view('chunker_api.views.flow_views.serve_flow_media'), name='serve_flow_media'),

    # 舆情时间线
    path('timeline/extract/', _lazy_view('chunker_api.views.timeline_views.extract_timeline'), name='extract_timeline'),
    path('timeline/stats/', _lazy_view('chunker_api.views.timeline_views.timeline_stats'), name='timeline_stats'),

    # ==================== 后台管理 API (Phase 0) ====================
    # 认证
    path('admin/auth/login/', _lazy_view('chunker_api.views.views_admin.admin_login'), name='admin_login'),
    path('admin/auth/refresh/', _lazy_view('chunker_api.views.views_admin.admin_token_refresh'), name='admin_token_refresh'),
    path('admin/auth/logout/', _lazy_view('chunker_api.views.views_admin.admin_logout'), name='admin_logout'),
    path('admin/auth/add-account/', _lazy_view('chunker_api.views.views_admin.admin_add_account'), name='admin_add_account'),
    path('admin/auth/change-password/', _lazy_view('chunker_api.views.views_admin.admin_change_password'), name='admin_change_password'),
    
    # 看板大屏与日志
    path('admin/dashboard/stats/', _lazy_view('chunker_api.views.views_admin.dashboard_stats'), name='admin_dashboard_stats'),
    path('admin/settings/logs/', _lazy_view('chunker_api.views.views_admin.admin_operation_logs'), name='admin_operation_logs'),
    
    # 知识库
    path('admin/kb/', _lazy_view('chunker_api.views.views_admin.admin_kb_list_create'), name='admin_kb_list_create'),
    path('admin/kb/<str:kb_id>/', _lazy_view('chunker_api.views.views_admin.admin_kb_detail'), name='admin_kb_detail'),
    
    # 文档
    path('admin/document/', _lazy_view('chunker_api.views.views_admin.admin_document_list'), name='admin_document_list'),
    path('admin/document/upload/', _lazy_view('chunker_api.views.views_admin.admin_document_upload'), name='admin_document_upload'),
    path('admin/document/<str:doc_id>/status/', _lazy_view('chunker_api.views.views_admin.admin_document_status'), name='admin_document_status'),
    path('admin/document/<str:doc_id>/edit-chunk/', _lazy_view('chunker_api.views.views_admin.admin_document_update_chunk'), name='admin_document_update_chunk'),
    path('admin/document/<str:doc_id>/', _lazy_view('chunker_api.views.views_admin.admin_document_detail'), name='admin_document_detail'),
    
    # 版本
    path('admin/document-version/upload/', _lazy_view('chunker_api.views.views_admin.admin_version_upload'), name='admin_version_upload'),
    path('admin/document-version/switch/', _lazy_view('chunker_api.views.views_admin.admin_version_switch'), name='admin_version_switch'),

    # ==================== 反馈闭环 (Phase 3) ====================
    path('chat/feedback/', _lazy_view('chunker_api.views.views_feedback.submit_feedback'), name='submit_feedback'),
    path('chat/feedback-types/', _lazy_view('chunker_api.views.views_feedback.get_feedback_types'), name='get_feedback_types'),
    
    path('admin/feedback/', _lazy_view('chunker_api.views.views_feedback.admin_feedback_list'), name='admin_feedback_list'),
    path('admin/feedback/<int:feedback_id>/', _lazy_view('chunker_api.views.views_feedback.admin_feedback_detail'), name='admin_feedback_detail'),
    path('admin/feedback/<int:feedback_id>/ignore/', _lazy_view('chunker_api.views.views_feedback.admin_feedback_ignore'), name='admin_feedback_ignore'),
    path('admin/feedback/<int:feedback_id>/offline-document/', _lazy_view('chunker_api.views.views_feedback.admin_feedback_offline_document'), name='admin_feedback_offline_document'),
    path('admin/feedback/<int:feedback_id>/edit-chunk/', _lazy_view('chunker_api.views.views_feedback.admin_feedback_update_chunk'), name='admin_feedback_update_chunk'),
]

# 开发环境下提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
