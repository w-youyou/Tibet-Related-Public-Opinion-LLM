# 分块器API服务

基于Django的文本分块器API服务，支持五种不同的分块策略。

## 功能特性

- **问答分块器**: 专门处理问答类文档，提取Q/A对
- **法律法规分块器**: 按"条"进行分块，适用于法律法规文档
- **语义分块器**: 基于语义相似度的智能分块
- **政策公告分块器**: 基于一级标题分块，适用于政策公告
- **表格分块器**: 专门处理表格数据，按行分块

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
python start_server.py
```

或者手动启动：

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## API接口

### 1. 健康检查
```
GET /api/health/
```

### 2. 获取分块器信息
```
GET /api/chunkers/
```

### 3. 文档分块
```
POST /api/chunk/
```

**请求参数:**
- `file`: 上传的文件
- `chunker_type`: 分块器类型 (qa, law, semantic, policy, table)

**响应格式:**
```json
{
  "success": true,
  "chunker_type": "qa",
  "file_name": "example.txt",
  "chunks": [
    {
      "id": 1,
      "content": "问：什么是人工智能？\n答：人工智能是...",
      "metadata": {
        "source_file": "example.txt",
        "intro": "..."
      }
    }
  ],
  "statistics": {
    "total_chunks": 3,
    "chunker_name": "问答分块器"
  }
}
```

## 支持的文件格式

- **文本文件**: .txt
- **PDF文档**: .pdf
- **Word文档**: .docx, .doc
- **Excel表格**: .xlsx, .xls

**注意**: .doc文件支持需要安装pywin32库，并且需要Windows系统和Microsoft Word。

## 测试API

运行测试脚本：

```bash
python test_api.py
```

## 分块器类型说明

### 1. 问答分块器 (qa)
- 适用于问答类文档
- 自动识别问题和答案
- 支持多种文档格式

### 2. 法律法规分块器 (law)
- 按"条"进行分块
- 提取章节信息
- 保持条文完整性

### 3. 语义分块器 (semantic)
- 基于语义相似度
- 智能边界识别
- 保持上下文连贯性

### 4. 政策公告分块器 (policy)
- 基于一级标题分块
- 处理表格数据
- 提取发布时间

### 5. 表格分块器 (table)
- 专门处理表格数据
- 按行分块
- 保持表头信息

## 错误处理

API会返回详细的错误信息：

```json
{
  "error": "错误描述",
  "supported_types": [".txt", ".pdf", ".docx"]
}
```

## 注意事项

1. 文件大小限制为50MB
2. 支持的文件格式有限制
3. 分块处理可能需要一些时间
4. 建议在生产环境中配置适当的超时设置

