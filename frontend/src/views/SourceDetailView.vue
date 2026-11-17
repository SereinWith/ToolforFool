<template>
  <div class="detail">
    <el-page-header @back="goBack" class="back-header">
      <template #content>
        <span class="detail-title">{{ source?.title || '文献详情' }}</span>
      </template>
    </el-page-header>

    <el-skeleton v-if="loading" :rows="6" animated />

    <el-card v-else-if="source" shadow="never" class="detail-card">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="来源站点">{{ source.site || '未知' }}</el-descriptions-item>
        <el-descriptions-item label="来源网址">
          <el-link :href="source.url" target="_blank" type="primary" :underline="false">
            {{ source.url }}
          </el-link>
        </el-descriptions-item>
        <el-descriptions-item label="抓取时间">
          {{ formatTime(source.crawled_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="概述">
          {{ source.summary || '暂无概述' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">
        <div class="content-header">
          <span>正文</span>
          <el-button
            v-if="source?.content"
            text
            type="primary"
            size="small"
            :loading="converting"
            :disabled="converting"
            @click="handleConvert"
          >
            {{ isSimplified ? '恢复原文' : '转简体' }}
          </el-button>
        </div>
      </el-divider>
      <div class="content">{{ displayContent || '暂无正文内容' }}</div>

      <template #footer>
        <el-button type="danger" :loading="deleting" @click="handleDelete">
          删除记录
        </el-button>
      </template>
    </el-card>

    <el-empty v-else description="未找到该记录" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'
import type { Source } from '@/types'

const route = useRoute()
const router = useRouter()

const id = Number(route.params.id)
const loading = ref(true)
const deleting = ref(false)
const source = ref<Source | null>(null)
const displayContent = ref('')
const isSimplified = ref(false)
const converting = ref(false)

async function fetchDetail() {
  loading.value = true
  try {
    source.value = await request.get<unknown, Source>(`/sources/${id}`)
    displayContent.value = source.value.content || ''
    isSimplified.value = false
  } catch {
    source.value = null
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确认删除该记录？此操作不可恢复。', '提示', {
      type: 'warning'
    })
  } catch {
    return
  }
  deleting.value = true
  try {
    await request.delete(`/sources/${id}`)
    ElMessage.success('已删除')
    router.replace('/')
  } catch {
    /* 错误已在拦截器中提示 */
  } finally {
    deleting.value = false
  }
}

async function handleConvert() {
  if (!source.value?.content) return
  if (isSimplified.value) {
    displayContent.value = source.value.content
    isSimplified.value = false
    return
  }
  converting.value = true
  try {
    const resp = await request.post<unknown, { text: string }>('/convert', {
      text: source.value.content,
      direction: 't2s'
    })
    displayContent.value = resp.text
    isSimplified.value = true
    ElMessage.success('已转为简体')
  } catch {
    /* 错误已在拦截器中提示 */
  } finally {
    converting.value = false
  }
}

function goBack() {
  router.back()
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleString('zh-CN')
}

onMounted(fetchDetail)
</script>

<style scoped>
.detail {
  max-width: 900px;
  margin: 0 auto;
}
.back-header {
  margin-bottom: 12px;
}
.detail-title {
  font-size: 1.1rem;
  font-weight: 600;
}
.content {
  white-space: pre-wrap;
  line-height: 1.9;
  font-size: 1rem;
  color: #303133;
  background: #fafafa;
  padding: 16px;
  border-radius: 4px;
}
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
</style>
