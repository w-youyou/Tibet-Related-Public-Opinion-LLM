from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    """扩展用户模型"""
    USER_TYPE_CHOICES = [
        ('personal', '个人用户'),
        ('enterprise', '企业用户'),
    ]

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='personal',
        verbose_name='用户类型'
    )
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='工号'
    )

    email = models.EmailField(unique=True, verbose_name='邮箱')
    age = models.IntegerField(null=True, blank=True, verbose_name='年龄')
    GENDER_CHOICES = [
        ('M', '男'),
        ('F', '女'),
        ('O', '其他'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True, verbose_name='性别')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        db_table = 'users'

    def __str__(self):
        return self.username


class KnowledgeBase(models.Model):
    """知识库模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='knowledge_bases', verbose_name='用户')
    name = models.CharField(max_length=200, verbose_name='知识库名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    collection_name = models.CharField(max_length=200, unique=True, verbose_name='Chroma集合名称')
    STATUS_CHOICES = [
        ('active', '运行中'),
        ('inactive', '已禁用'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '知识库'
        verbose_name_plural = '知识库'
        db_table = 'knowledge_bases'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def save(self, *args, **kwargs):
        # 如果collection_name为空，生成一个唯一的名称
        if not self.collection_name:
            self.collection_name = f"kb_{self.user.username}_{self.id.hex[:8]}"
        super().save(*args, **kwargs)


class ChatSession(models.Model):
    """聊天会话"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions', verbose_name='用户')
    title = models.CharField(max_length=200, verbose_name='标题')
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions', verbose_name='知识库')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '聊天会话'
        verbose_name_plural = '聊天会话'
        db_table = 'chat_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ChatMessage(models.Model):
    """聊天消息"""
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', '助手'),
    ]
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', verbose_name='会话')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name='角色')
    content = models.TextField(verbose_name='内容')

    # 旧字段：兼容历史消息与旧前端
    sources = models.JSONField(null=True, blank=True, verbose_name='参考资料')
    images = models.JSONField(null=True, blank=True, verbose_name='图片')

    # RAG v1 字段（方案1：文档静态元数据 + 动态命中分离）
    trace_id = models.CharField(max_length=64, null=True, blank=True, verbose_name='追踪ID')
    citations = models.JSONField(null=True, blank=True, verbose_name='引用来源（文档级静态信息）')
    retrieval_hits = models.JSONField(null=True, blank=True, verbose_name='检索命中（chunk级动态信息）')
    evidence_spans = models.JSONField(null=True, blank=True, verbose_name='证据片段')
    retrieval_stats = models.JSONField(null=True, blank=True, verbose_name='检索统计')
    refusal = models.JSONField(null=True, blank=True, verbose_name='拒答信息')
    suggested_next_questions = models.JSONField(null=True, blank=True, verbose_name='引导式追问')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '聊天消息'
        verbose_name_plural = '聊天消息'
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.session.title} - {self.role}"
class AdminUser(models.Model):
    """独立管理员模型"""
    ROLE_CHOICES = [
        ('SUPER_ADMIN', '超级管理员'),
        ('KB_ADMIN', '知识库管理员'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID')
    username = models.CharField(max_length=150, unique=True, verbose_name='用户名')
    password = models.CharField(max_length=128, verbose_name='密码')
    email = models.EmailField(unique=True, verbose_name='邮箱')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='KB_ADMIN', verbose_name='角色')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'admin_users'
        verbose_name = '系统管理员'
        verbose_name_plural = '系统管理员'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Document(models.Model):
    """逻辑文档模型"""
    STATUS_CHOICES = [
        ('active', '已启用'),
        ('inactive', '已禁用'),
        ('deleted', '已删除'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID')
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='documents', verbose_name='所属知识库')
    name = models.CharField(max_length=255, verbose_name='文件名')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='文档状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'documents'
        verbose_name = '知识库文档'
        verbose_name_plural = '知识库文档'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class DocumentVersion(models.Model):
    """物理文档版本模型"""
    STATUS_CHOICES = [
        ('current', '当前主版本'),
        ('historical', '历史版本'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions', verbose_name='所属逻辑文档')
    version_number = models.PositiveIntegerField(verbose_name='版本号')
    file_path = models.CharField(max_length=500, verbose_name='物理存储路径')
    file_size = models.PositiveIntegerField(verbose_name='文件大小(字节)')
    chunk_count = models.PositiveIntegerField(default=0, verbose_name='分块数量')
    embedding_count = models.PositiveIntegerField(default=0, verbose_name='向量化数量')
    chunker_type = models.CharField(max_length=50, default='semantic', verbose_name='分块器类型')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='historical', verbose_name='版本状态')
    
    uploaded_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='上传用户(前台)')
    uploaded_by_admin = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='上传管理员(后台)')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    remark = models.CharField(max_length=500, blank=True, null=True, verbose_name='备注说明')

    class Meta:
        db_table = 'document_versions'
        unique_together = ('document', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.document.name} - v{self.version_number}"


class OperationLog(models.Model):
    """管理员操作审计日志"""
    id = models.BigAutoField(primary_key=True)
    admin_user = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, verbose_name='操作管理员')
    action = models.CharField(max_length=50, verbose_name='操作类型')
    details = models.TextField(verbose_name='详细描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        db_table = 'operation_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.admin_user.username if self.admin_user else '系统'} - {self.action}"







class Feedback(models.Model):
    """用户反馈主表"""
    STATUS_CHOICES = [
        ('PENDING', '待处理'),
        ('PROCESSING', '处理中'),
        ('RESOLVED', '已解决'),
        ('IGNORED', '已忽略'),
    ]
    TYPE_CHOICES = [
        ('ANSWER_ERROR', '回答错误'),
        ('HALLUCINATION', '幻觉内容'),
        ('DOCUMENT_OUTDATED', '内容过期'),
        ('RETRIEVAL_ERROR', '引用错误'),
        ('OTHER', '其他'),
    ]

    id = models.BigAutoField(primary_key=True)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='feedbacks', verbose_name='关联消息')
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='feedbacks', verbose_name='关联会话')
    question = models.TextField(verbose_name='用户提问快照')
    answer = models.TextField(verbose_name='模型回答快照')
    feedback_type = models.CharField(max_length=50, choices=TYPE_CHOICES, verbose_name='反馈类型')
    feedback_comment = models.TextField(blank=True, null=True, verbose_name='用户备注')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='处理状态')
    handler = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_feedbacks', verbose_name='处理人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'feedback'
        verbose_name = '用户反馈'
        verbose_name_plural = '用户反馈'
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback {self.id} - {self.get_feedback_type_display()}"

class FeedbackDocument(models.Model):
    """反馈关联的召回文档"""
    id = models.BigAutoField(primary_key=True)
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name='feedback_documents')
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    document_version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'feedback_document'

class FeedbackChunk(models.Model):
    """反馈关联的召回Chunk"""
    id = models.BigAutoField(primary_key=True)
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name='feedback_chunks')
    chunk_id = models.CharField(max_length=255, verbose_name='Chunk ID')
    content = models.TextField(verbose_name='Chunk内容快照', null=True, blank=True)
    score = models.FloatField(verbose_name='检索分数', null=True, blank=True)
    rank = models.IntegerField(verbose_name='检索排名', null=True, blank=True)

    class Meta:
        db_table = 'feedback_chunk'

class FeedbackProcessLog(models.Model):
    """反馈处理流转日志"""
    ACTION_CHOICES = [
        ('DOCUMENT_OFFLINE', '下架文档'),
        ('CHUNK_UPDATED', '更新Chunk'),
        ('DOCUMENT_REPUBLISHED', '重新发布文档'),
        ('IGNORED', '忽略反馈'),
        ('STATUS_CHANGED', '状态变更'),
    ]

    id = models.BigAutoField(primary_key=True)
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name='process_logs')
    operator = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    remark = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedback_process_log'
        ordering = ['-created_at']
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedback_process_log'
        ordering = ['-created_at']


class UserPersona(models.Model):
    """
    用户画像（单表）
    用于 RAG 推理
    """

    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='persona'
    )

    # ===== 角色维度（核心） =====
    ROLE_CHOICES = [
        ('enterprise', '企业用户'),
        ('external', '外来用户'),
        ('local', '本地居民'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='external',
        verbose_name='用户角色'
    )

    # ===== 年龄段 =====
    AGE_GROUP_CHOICES = [
        ('youth', '青年'),
        ('elder', '老年'),
    ]
    age_group = models.CharField(
        max_length=10,
        choices=AGE_GROUP_CHOICES,
        default='youth',
        verbose_name='年龄段'
    )

    # ===== 活跃度原始数据 =====
    total_questions = models.PositiveIntegerField(default=0)
    active_days = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)

    # ===== 活跃度等级（系统计算） =====
    FREQUENCY_CHOICES = [
        ('new', '新用户'),
        ('normal', '普通用户'),
        ('high', '高频用户'),
    ]
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default='new',
        verbose_name='活跃度'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_personas'
        verbose_name = '用户画像'
        verbose_name_plural = '用户画像'
