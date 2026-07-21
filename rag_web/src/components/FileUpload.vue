<template>
  <div class="file-upload">
    <div class="upload-card">
      <div class="upload-area" 
           :class="{ 'drag-over': isDragOver, 'has-file': uploadedFile }"
           @dragover.prevent="handleDragOver"
           @dragleave.prevent="handleDragLeave"
           @drop.prevent="handleDrop"
           @click="triggerFileInput">
        
        <input 
          ref="fileInput"
          type="file" 
          accept=".txt,.pdf,.doc,.docx,.md"
          @change="handleFileSelect"
          style="display: none"
        />
        
        <div v-if="!uploadedFile" class="upload-content">
          <div class="upload-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          </div>
          <h3>拖拽文件到此处或点击选择文件</h3>
          <p>支持格式：TXT, PDF, DOC, DOCX, MD</p>
          <div class="file-size-limit">最大文件大小：50MB</div>
        </div>
        
        <div v-else class="file-info">
          <div class="file-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </div>
          <div class="file-details">
            <h4>{{ uploadedFile.name }}</h4>
            <p>{{ formatFileSize(uploadedFile.size) }}</p>
            <div class="file-actions">
              <button @click.stop="removeFile" class="remove-btn">移除</button>
              <button @click.stop="triggerFileInput" class="change-btn">更换</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// Props
const props = defineProps<{
  isProcessing?: boolean
}>()

// Emits
const emit = defineEmits<{
  fileUploaded: [file: File]
}>()

// 响应式数据
const fileInput = ref<HTMLInputElement>()
const uploadedFile = ref<File | null>(null)
const isDragOver = ref(false)

// 触发文件选择
const triggerFileInput = () => {
  if (props.isProcessing) return
  fileInput.value?.click()
}

// 处理文件选择
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    processFile(file)
  }
}

// 处理拖拽悬停
const handleDragOver = (event: DragEvent) => {
  if (props.isProcessing) return
  isDragOver.value = true
}

// 处理拖拽离开
const handleDragLeave = () => {
  isDragOver.value = false
}

// 处理文件拖拽放置
const handleDrop = (event: DragEvent) => {
  if (props.isProcessing) return
  isDragOver.value = false
  
  const files = event.dataTransfer?.files
  const file = files?.[0]
  if (file) {
    processFile(file)
  }
}

// 处理文件
const processFile = (file: File) => {
  // 检查文件类型
  const allowedTypes = [
    'text/plain',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/markdown'
  ]
  
  const allowedExtensions = ['.txt', '.pdf', '.doc', '.docx', '.md']
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
  
  if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
    alert('不支持的文件格式，请选择 TXT, PDF, DOC, DOCX 或 MD 文件')
    return
  }
  
  // 检查文件大小 (50MB)
  if (file.size > 50 * 1024 * 1024) {
    alert('文件大小超过 50MB 限制')
    return
  }
  
  uploadedFile.value = file
  emit('fileUploaded', file)
}

// 移除文件
const removeFile = () => {
  uploadedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.file-upload {
  margin-bottom: 2rem;
}

.upload-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
}

.upload-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.upload-area {
  padding: 3rem 2rem;
  border: 2px dashed #e1e5e9;
  border-radius: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafbfc;
}

.upload-area:hover {
  border-color: #667eea;
  background: #f8f9ff;
}

.upload-area.drag-over {
  border-color: #667eea;
  background: #f0f4ff;
  transform: scale(1.02);
}

.upload-area.has-file {
  border-color: #10b981;
  background: #f0fdf4;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.upload-icon {
  font-size: 4rem;
  opacity: 0.6;
}

.upload-content h3 {
  margin: 0;
  color: #374151;
  font-size: 1.5rem;
  font-weight: 600;
}

.upload-content p {
  margin: 0;
  color: #6b7280;
  font-size: 1rem;
}

.file-size-limit {
  color: #9ca3af;
  font-size: 0.875rem;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  text-align: left;
}

.file-icon {
  font-size: 3rem;
  opacity: 0.8;
}

.file-details {
  flex: 1;
}

.file-details h4 {
  margin: 0 0 0.5rem 0;
  color: #374151;
  font-size: 1.25rem;
  font-weight: 600;
}

.file-details p {
  margin: 0 0 1rem 0;
  color: #6b7280;
  font-size: 0.875rem;
}

.file-actions {
  display: flex;
  gap: 0.75rem;
}

.remove-btn, .change-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.remove-btn {
  background: #fee2e2;
  color: #dc2626;
}

.remove-btn:hover {
  background: #fecaca;
}

.change-btn {
  background: #dbeafe;
  color: #2563eb;
}

.change-btn:hover {
  background: #bfdbfe;
}

@media (max-width: 768px) {
  .upload-area {
    padding: 2rem 1rem;
  }
  
  .upload-content h3 {
    font-size: 1.25rem;
  }
  
  .file-info {
    flex-direction: column;
    text-align: center;
  }
  
  .file-actions {
    justify-content: center;
  }
}
</style>
