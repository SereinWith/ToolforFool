<template>
  <div class="convert">
    <el-card shadow="never" class="convert-card">
      <template #header>
        <span>繁简转换工具</span>
      </template>
      <el-form label-position="top">
        <el-form-item label="转换方向">
          <el-radio-group v-model="direction">
            <el-radio value="t2s">繁体 → 简体</el-radio>
            <el-radio value="s2t">简体 → 繁体</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="输入文本">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="8"
            placeholder="请输入需要转换的文字…"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="converting" :disabled="!inputText.trim()" @click="handleConvert">
            开始转换
          </el-button>
          <el-button :disabled="!inputText" @click="inputText = ''; outputText = ''">清空</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="outputText" shadow="never" class="result-card">
      <template #header>
        <div class="result-header">
          <span>转换结果</span>
          <el-button text type="primary" @click="copyResult">复制</el-button>
        </div>
      </template>
      <el-input v-model="outputText" type="textarea" :rows="10" readonly />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const direction = ref<'t2s' | 's2t'>('t2s')
const inputText = ref('')
const outputText = ref('')
const converting = ref(false)

async function handleConvert() {
  if (!inputText.value.trim()) return
  converting.value = true
  try {
    const resp = await request.post<unknown, { text: string }>('/convert', {
      text: inputText.value,
      direction: direction.value
    })
    outputText.value = resp.text
    ElMessage.success('转换完成')
  } catch {
    /* 错误已在拦截器中提示 */
  } finally {
    converting.value = false
  }
}

function copyResult() {
  navigator.clipboard.writeText(outputText.value).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}
</script>

<style scoped>
.convert {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
