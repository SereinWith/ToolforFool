<template>
  <div class="search">
    <el-card shadow="never" class="search-card">
      <template #header>
        <span>关键词检索（支持 AI 语义扩展）</span>
      </template>
      <el-form label-position="top">
        <el-form-item label="关键词（多个用逗号或换行分隔）">
          <el-input
            v-model="keywordsText"
            type="textarea"
            :rows="2"
            placeholder="例如：黄帝, 轩辕, 神农"
          />
        </el-form-item>
        <el-form-item label="指定古籍 URL（可选，每行一个；留空则在已入库文献中检索）">
          <el-input
            v-model="urlsText"
            type="textarea"
            :rows="3"
            placeholder="https://www.shidianguji.com/book/LS0001/chapter/..."
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="useAiExpansion">
            AI 语义扩展（用近义词/别称扩大检索范围，未配置 API Key 时使用内置词典）
          </el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="searching" @click="handleSearch">
            开始检索
          </el-button>
          <el-dropdown trigger="click" @command="handleExport" :disabled="!results.length">
            <el-button>导出结果</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="json">JSON</el-dropdown-item>
                <el-dropdown-item command="csv">CSV</el-dropdown-item>
                <el-dropdown-item command="txt">TXT</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="result-card" v-if="results.length || searching">
      <template #header>
        <span>检索结果（{{ results.length }} 条）</span>
      </template>
      <el-skeleton v-if="searching" :rows="4" animated />
      <el-empty v-else-if="!results.length" description="未找到匹配内容" />
      <div v-else class="result-list">
        <div
          v-for="item in results"
          :key="item.id"
          class="result-item"
        >
          <div class="result-meta">
            <el-tag size="small" type="success">{{ item.keyword }}</el-tag>
            <span class="result-title">{{ item.source_title || '无标题' }}</span>
            <span class="result-site">{{ item.site }}</span>
            <el-button
              text
              type="primary"
              size="small"
              class="convert-btn"
              @click="handleConvert(item)"
            >
              {{ item.isSimplified ? '恢复原文' : '转简体' }}
            </el-button>
          </div>
          <p class="result-excerpt" v-html="highlight(item.displayExcerpt || item.excerpt, item.matched_keyword)"></p>
          <a :href="item.source_url" target="_blank" class="result-url">
            {{ item.source_url }}
          </a>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

interface SearchResult {
  id: number
  keyword: string
  source_url: string
  source_title: string | null
  site: string | null
  excerpt: string
  matched_keyword: string
  created_at: string
  displayExcerpt?: string
  isSimplified?: boolean
}

const keywordsText = ref('')
const urlsText = ref('')
const useAiExpansion = ref(false)
const searching = ref(false)
const results = ref<SearchResult[]>([])

function parseList(text: string): string[] {
  return text
    .split(/[\n,，;；]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

async function handleSearch() {
  const keywords = parseList(keywordsText.value)
  if (!keywords.length) {
    ElMessage.warning('请输入至少一个关键词')
    return
  }
  const urls = parseList(urlsText.value)

  searching.value = true
  results.value = []
  try {
    const endpoint = useAiExpansion.value ? '/ai/search' : '/search'
    results.value = await request.post<unknown, SearchResult[]>(endpoint, {
      keywords,
      urls: urls.length ? urls : undefined
    })
    ElMessage.success(`检索完成，共 ${results.value.length} 条结果`)
  } catch {
    /* 错误已在拦截器中提示 */
  } finally {
    searching.value = false
  }
}

async function loadResults() {
  try {
    results.value = await request.get<unknown, SearchResult[]>('/search/results')
  } catch {
    results.value = []
  }
}

function handleExport(format: string) {
  // 直接打开导出接口 URL，触发浏览器下载
  window.open(`/api/search/export?format=${format}`, '_blank')
}

function highlight(text: string, keyword: string) {
  if (!keyword) return text
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const re = new RegExp(`(${escaped})`, 'gi')
  return text.replace(re, '<mark>$1</mark>')
}

async function handleConvert(item: SearchResult) {
  if (item.isSimplified) {
    item.displayExcerpt = undefined
    item.isSimplified = false
    return
  }
  try {
    const resp = await request.post<unknown, { text: string }>('/convert', {
      text: item.excerpt,
      direction: 't2s'
    })
    item.displayExcerpt = resp.text
    item.isSimplified = true
    ElMessage.success('已转为简体')
  } catch {
    /* 错误已在拦截器中提示 */
  }
}

onMounted(loadResults)
</script>

<style scoped>
.search {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1100px;
  margin: 0 auto;
}
.result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.result-item {
  padding: 12px 16px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}
.result-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.convert-btn {
  margin-left: auto;
}
.result-title {
  font-weight: 600;
  color: #303133;
}
.result-site {
  color: #909399;
  font-size: 0.85rem;
}
.result-excerpt {
  margin: 0 0 8px;
  line-height: 1.8;
  color: #606266;
  white-space: pre-wrap;
}
.result-excerpt :deep(mark) {
  background: #fff3a3;
  padding: 0 2px;
  border-radius: 2px;
}
.result-url {
  font-size: 0.8rem;
  color: #409eff;
  word-break: break-all;
}
</style>
