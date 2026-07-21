# 前端功能实现总结

## 已实现的功能

### 1. 端口问题修复
- **问题**: `npm run dev` 报错 `EACCES: permission denied ::1:5173`
- **解决方案**: 修改 `vite.config.ts`，将端口从5173改为3000，并添加host配置
- **修改文件**: `rag_web/vite.config.ts`

### 2. 登录注册功能

#### 登录注册模态框 (`AuthModal.vue`)
- **位置**: `rag_web/src/components/AuthModal.vue`
- **功能特性**:
  - 登录和注册两个标签页，可切换
  - **登录表单字段**: 用户名/邮箱、密码
  - **注册表单字段**: 用户名、密码（至少6位）、确认密码、邮箱、年龄（数字）、性别（男/女/其他）
  - 表单验证
  - 现代化UI设计，带动画效果
  - 成功后触发回调事件

#### 主界面更新 (`ChatView.vue`)
- **位置**: `rag_web/src/views/ChatView.vue`
- **功能特性**:
  - 未登录时显示"登录"按钮
  - 点击登录按钮弹出登录/注册模态框
  - 登录成功后显示用户信息（头像、用户名、邮箱）
  - 登录状态控制: `isLoggedIn` 默认为 `false`
  - 退出登录功能
  - **后端 API 已集成**: 实际调用 `/api/auth/login/`、`/api/auth/register/`、`/api/auth/logout/`、`/api/auth/user/`

### 3. 聊天功能

#### 聊天界面 (`ChatView.vue`)
- **位置**: `rag_web/src/views/ChatView.vue`
- **功能特性**:
  - 流式问答（SSE），实时显示回答
  - 多模态支持（文本 + 图片）
  - 聊天记录持久化（后端存储会话和消息）
  - 新建对话、重命名对话、删除对话
  - 自动调整高度的输入框
  - Markdown 渲染 + DOMPurify 安全过滤

#### API 集成
- 创建会话: `POST /api/chat/sessions/create/`
- 列出会话: `GET /api/chat/sessions/`
- 获取消息: `GET /api/chat/sessions/<session_id>/messages/`
- 删除会话: `POST /api/chat/sessions/<session_id>/delete/`
- 重命名会话: `POST /api/chat/sessions/<session_id>/rename/`
- 流式问答: `POST /api/qa/hybrid/stream/`
- 非流式问答: `POST /api/qa/hybrid/`
- 多模态问答: `POST /api/qa/ask/`

### 4. 知识库管理

#### 知识库列表页 (`KnowledgeBaseManage.vue`)
- **位置**: `rag_web/src/views/KnowledgeBaseManage.vue`
- **功能特性**:
  - 卡片式知识库列表（名称、描述、创建时间、更新时间）
  - 编辑知识库名称和描述
  - 删除知识库
  - 点击进入知识库详情（跳转到 ChunkerDemo）
  - **检索范围选择器**（2026-05-09 从 ChatView 迁移至此）

#### 文档分块与入库 (`ChunkerDemo.vue`)
- **位置**: `rag_web/src/views/ChunkerDemo.vue`
- **功能特性**:
  - 文件上传（支持多种格式）
  - 分块器选择（basic / advanced / specialized）
  - 分块参数配置
  - 分块结果预览
  - 知识库创建与文档入库
  - 流程图自动提取

#### API 集成
- 列出知识库: `GET /api/knowledge-bases/`
- 创建知识库: `POST /api/knowledge-bases/create/`
- 获取知识库: `GET /api/knowledge-bases/<kb_id>/`
- 删除知识库: `POST /api/knowledge-bases/<kb_id>/delete/`
- 文档分块: `POST /api/chunk/`
- 获取分块器信息: `GET /api/chunkers/`

### 5. 流程图功能

#### 流程图生成页 (`FlowDiagramView.vue`)
- **位置**: `rag_web/src/views/FlowDiagramView.vue`
- **功能特性**:
  - 从文本抽取流程
  - 从文件自动生成流程图
  - 流程图可视化展示

#### API 集成
- 文本抽取: `POST /api/flow/extract-text/`
- 文件自动生成: `POST /api/flow/auto/`
- 媒体文件访问: `GET /api/flow/media/<file_name>`

### 6. 状态管理

#### Pinia Store
- **位置**: `rag_web/src/stores/`
- **已有 Store**:
  - `kbFilter.ts` — 知识库筛选状态（跨页面共享，持久化到 localStorage）
    - `selectedKnowledgeBase`: 当前选中的知识库 ID（空字符串表示所有知识库）
    - `setSelected(id)`: 更新选择
    - `clear()`: 清空选择（登出时调用）

### 7. 路由配置
- **修改文件**: `rag_web/src/router/index.ts`
- 主页路径: `/` → ChatView
- 分块演示: `/chunker` → ChunkerDemo
- 知识库管理: `/knowledge-bases` → KnowledgeBaseManage
- 流程图: `/flow-diagram` → FlowDiagramView
- 用户资料: `/profile` → ProfileView
- 关于: `/about` → AboutView

## 设计特点

### UI/UX
- 现代化设计风格
- 流畅的动画过渡
- 清晰的视觉层次
- 响应式布局
- 友好的交互反馈

### 代码特点
- TypeScript 类型安全
- Vue 3 Composition API
- 组件化设计
- 模块化样式
- Pinia 状态管理

## 文件结构

```
rag_web/
├── src/
│   ├── components/
│   │   ├── AuthModal.vue          # 登录注册组件
│   │   ├── ChunkResults.vue       # 分块结果展示
│   │   ├── ChunkerSelector.vue    # 分块器选择
│   │   └── FileUpload.vue         # 文件上传
│   ├── views/
│   │   ├── ChatView.vue           # 聊天主界面
│   │   ├── ChunkerDemo.vue        # 文档分块与知识库创建
│   │   ├── KnowledgeBaseManage.vue # 知识库列表管理
│   │   ├── FlowDiagramView.vue    # 流程图生成
│   │   ├── ProfileView.vue        # 用户资料
│   │   └── AboutView.vue
│   ├── stores/
│   │   └── kbFilter.ts            # 知识库筛选状态管理
│   ├── services/
│   │   └── api.ts                 # API 封装
│   ├── router/
│   │   └── index.ts               # 路由配置
│   └── main.ts
├── vite.config.ts                 # Vite 配置
└── package.json
```

## 运行说明

### 启动开发服务器
```bash
cd rag_web
npm run dev
```

### 访问地址
- 本地访问: http://localhost:3000
- 网络访问: http://[你的IP]:3000

## 技术栈

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- marked (Markdown 渲染)
- DOMPurify (XSS 防护)
