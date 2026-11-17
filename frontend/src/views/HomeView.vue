<template>
  <div class="home">
    <el-card shadow="never" class="crawl-card">
      <template #header>
        <span>抓取文献（第一档：URL + 概述记录）</span>
      </template>
      <el-form :model="form" label-width="auto" @submit.prevent="handleCrawl">
        <el-form-item label="网址">
          <el-input
            v-model="form.url"
            placeholder="请输入古籍页面地址，如识典古籍章节页 / 古诗文网"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleCrawl">
            抓取并记录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="list-card">
      <template #header>
        <div class="list-header">
          <span>已记录文献</span>
          <el-button text type="primary" @click="fetchList">刷新</el-button>
        </div>
      </template>
      <el-empty v-if="!sources.length" description="暂无记录" />
      <el-table v-else :data="sources" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="site" label="来源站点" width="120" />
        <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="goDetail(row.id)">
              详情
            </el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'
import type { Source } from '@/types'

const router = useRouter()
const form = reactive({ url: '' })
const loading = ref(false)
const sources = ref<Source[]>([])

async function fetchList() {
  try {
    sources.value = await request.get<unknown, Source[]>('/sources')
  } catch {
    /* 错误已在拦截器中提示 */
  }
}

async function handleCrawl() {
  if (!form.url.trim()) {
    ElMessage.warning('请输入网址')
    return
  }
  loading.value = true
  try {
    await request.post('/sources/crawl', { url: form.url.trim() })
    ElMessage.success('抓取成功')
    form.url = ''
    await fetchList()
  } catch {
    /* 错误已在拦截器中提示 */
  } finally {
    loading.value = false
  }
}

async function handleDelete(row: Source) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.title || row.id}」？`, '提示', {
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await request.delete(`/sources/${row.id}`)
    ElMessage.success('已删除')
    await fetchList()
  } catch {
    /* 错误已在拦截器中提示 */
  }
}

function goDetail(id: number) {
  router.push(`/sources/${id}`)
}

onMounted(fetchList)
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1100px;
  margin: 0 auto;
}
.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
