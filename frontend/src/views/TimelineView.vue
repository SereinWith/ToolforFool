<template>
  <div class="timeline">
    <el-card shadow="never" class="action-card">
      <div class="action-row">
        <el-button type="primary" :loading="building" @click="handleBuild">
          从已入库文献构建人物时间线
        </el-button>
        <span class="hint">将从已抓取的古籍正文中提取人物与相关事件</span>
      </div>
    </el-card>

    <div class="content" v-if="persons.length">
      <el-card shadow="never" class="persons-card">
        <template #header><span>人物列表（{{ persons.length }}）</span></template>
        <el-scrollbar height="60vh">
          <div
            v-for="p in persons"
            :key="p.name"
            class="person-item"
            :class="{ active: selectedPerson === p.name }"
            @click="selectPerson(p.name)"
          >
            <span class="person-name">{{ p.name }}</span>
            <el-tag size="small" type="info">{{ p.event_count }}</el-tag>
          </div>
        </el-scrollbar>
      </el-card>

      <el-card shadow="never" class="events-card">
        <template #header>
          <span>{{ selectedPerson || '请选择人物' }} 的时间线</span>
        </template>
        <el-empty v-if="!selectedPerson" description="点击左侧人物查看其事件" />
        <el-timeline v-else>
          <el-timeline-item
            v-for="ev in events"
            :key="ev.id"
            :timestamp="ev.time_ref || '时间不详'"
            placement="top"
          >
            <p class="event-text">{{ ev.event_text }}</p>
            <a :href="ev.source_url" target="_blank" class="event-source">
              {{ ev.source_title || ev.source_url }}
            </a>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </div>

    <el-empty v-else-if="!building" description="尚未构建时间线，请点击上方按钮" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

interface Person {
  name: string
  event_count: number
}

interface PersonEvent {
  id: number
  person_name: string
  event_text: string
  time_ref: string | null
  source_url: string
  source_title: string | null
}

const persons = ref<Person[]>([])
const selectedPerson = ref('')
const events = ref<PersonEvent[]>([])
const building = ref(false)

async function handleBuild() {
  building.value = true
  try {
    const resp = await request.post<unknown, { persons: Person[] }>('/timeline/build', {})
    persons.value = resp.persons || []
    selectedPerson.value = ''
    events.value = []
    ElMessage.success(`构建完成，共 ${persons.value.length} 个人物`)
  } catch {
    /* 错误已在拦截器中提示 */
  } finally {
    building.value = false
  }
}

async function selectPerson(name: string) {
  selectedPerson.value = name
  try {
    events.value = await request.get<unknown, PersonEvent[]>(`/timeline/persons/${encodeURIComponent(name)}`)
  } catch {
    events.value = []
  }
}
</script>

<style scoped>
.timeline {
  max-width: 1100px;
  margin: 0 auto;
}
.action-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.hint {
  color: #909399;
  font-size: 0.85rem;
}
.content {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  margin-top: 16px;
}
.person-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}
.person-item:hover {
  background: #f5f7fa;
}
.person-item.active {
  background: #ecf5ff;
  color: #409eff;
}
.person-name {
  font-weight: 500;
}
.event-text {
  margin: 0 0 4px;
  line-height: 1.7;
}
.event-source {
  font-size: 0.8rem;
  color: #909399;
  word-break: break-all;
}
@media (max-width: 768px) {
  .content {
    grid-template-columns: 1fr;
  }
}
</style>
