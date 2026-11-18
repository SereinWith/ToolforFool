<template>
  <div class="ocr">
    <el-card shadow="never" class="ocr-card">
      <template #header>
        <span>OCR 文字识别（阶段三）</span>
      </template>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      >
        上传古籍图片，自动识别文字。系统按优先级自动选择：视觉大模型 → 百度云 OCR → 本地 PaddleOCR。
        古籍常用繁体，识别结果可一键转简体。
      </el-alert>
      <el-upload
        drag
        action=""
        :auto-upload="false"
        :show-file-list="false"
        accept="image/*"
        :on-change="handleFileChange"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">将图片拖到此处，或<em>点击上传</em></div>
      </el-upload>
      <div v-if="previewUrl" class="preview">
        <img :src="previewUrl" alt="预览" />
      </div>
      <el-button
        type="primary"
        :loading="recognizing"
        :disabled="!file"
        style="margin-top: 16px"
        @click="handleRecognize"
      >
        开始识别
      </el-button>
    </el-card>

    <el-card v-if="resultText" shadow="never" class="result-card">
      <template #header>
        <div class="result-header">
          <span>识别结果</span>
          <div class="result-actions">
            <el-button
              text
              type="primary"
              :loading="converting"
              :disabled="converting"
              @click="handleConvert"
            >
              {{ isSimplified ? '恢复原文' : '转简体' }}
            </el-button>
            <el-button text type="primary" @click="copyResult">复制</el-button>
          </div>
        </div>
      </template>
      <el-input
        v-model="resultText"
        type="textarea"
        :rows="12"
        readonly
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import request from '@/api/request'

const file = ref<File | null>(null)
const previewUrl = ref('')
const recognizing = ref(false)
const resultText = ref('')
const originalText = ref('')
const isSimplified = ref(false)
const converting = ref(false)

function handleFileChange(uploadFile: any) {
  const f = uploadFile.raw as File
  if (!f.type.startsWith('image/')) {
    ElMessage.warning('请上传图片文件')
    return
  }
  file.value = f
  previewUrl.value = URL.createObjectURL(f)
  resultText.value = ''
  originalText.value = ''
  isSimplified.value = false
}

async function handleRecognize() {
  if (!file.value) return
  recognizing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    // 不传 Content-Type，让 axios 自动生成带 boundary 的 multipart/form-data
    // 云端 OCR / 视觉大模型响应较慢，单独设置较长超时
    const resp = await request.post<
      unknown,
      { text: string; filename: string; provider: string }
    >('/ai/ocr', formData, { timeout: 180000 })
    resultText.value = resp.text || '（未识别到文字）'
    originalText.value = resultText.value
    isSimplified.value = false
    ElMessage.success(`识别完成（${resp.provider}）`)
  } catch {
    /* 错误已在拦截器中提示 */
  } finally {
    recognizing.value = false
  }
}

async function handleConvert() {
  if (isSimplified.value) {
    resultText.value = originalText.value
    isSimplified.value = false
    return
  }
  converting.value = true
  try {
    const resp = await request.post<unknown, { text: string }>('/convert', {
      text: originalText.value,
      direction: 't2s'
    })
    resultText.value = resp.text
    isSimplified.value = true
    ElMessage.success('已转为简体')
  } catch {
    /* 错误已在拦截器中提示 */
  } finally {
    converting.value = false
  }
}

function copyResult() {
  navigator.clipboard.writeText(resultText.value).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}
</script>

<style scoped>
.ocr {
  max-width: 800px;
  margin: 0 auto;
}
.preview {
  margin-top: 16px;
  text-align: center;
}
.preview img {
  max-width: 100%;
  max-height: 400px;
  border-radius: 6px;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.result-actions {
  display: flex;
  gap: 4px;
}
</style>
