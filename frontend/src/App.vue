<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <span class="app-title">ToolForFool</span>
      <!-- 桌面端水平菜单 -->
      <el-menu
        :default-active="activeMenu"
        mode="horizontal"
        background-color="#409eff"
        text-color="#fff"
        active-text-color="#ffd04b"
        router
        class="app-nav desktop-nav"
      >
        <el-menu-item index="/">抓取入库</el-menu-item>
        <el-menu-item index="/search">关键词检索</el-menu-item>
        <el-menu-item index="/ocr">OCR 识别</el-menu-item>
        <el-menu-item index="/timeline">人物时间线</el-menu-item>
        <el-menu-item index="/convert">繁简转换</el-menu-item>
      </el-menu>
      <!-- 移动端菜单按钮 -->
      <el-button
        class="mobile-menu-btn"
        text
        @click="drawerVisible = true"
      >
        <el-icon><Menu /></el-icon>
      </el-button>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>

    <!-- 移动端抽屉菜单 -->
    <el-drawer
      v-model="drawerVisible"
      direction="rtl"
      size="240px"
      :with-header="false"
    >
      <el-menu
        :default-active="activeMenu"
        background-color="#409eff"
        text-color="#fff"
        active-text-color="#ffd04b"
        router
        @select="drawerVisible = false"
      >
        <el-menu-item index="/">抓取入库</el-menu-item>
        <el-menu-item index="/search">关键词检索</el-menu-item>
        <el-menu-item index="/ocr">OCR 识别</el-menu-item>
        <el-menu-item index="/timeline">人物时间线</el-menu-item>
        <el-menu-item index="/convert">繁简转换</el-menu-item>
      </el-menu>
    </el-drawer>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => route.path)
const drawerVisible = ref(false)
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #409eff;
  color: #fff;
}
.app-title {
  font-size: 1.1rem;
  font-weight: 600;
  white-space: nowrap;
}
.app-nav {
  border-bottom: none;
  flex: 1;
}
.desktop-nav {
  display: flex;
}
.mobile-menu-btn {
  display: none;
  color: #fff;
  font-size: 1.4rem;
}
.app-main {
  padding: 16px;
}

/* 移动端适配：宽度 <= 768px 时隐藏水平菜单，显示抽屉按钮 */
@media (max-width: 768px) {
  .app-header {
    gap: 8px;
    padding: 0 12px;
  }
  .app-title {
    font-size: 0.95rem;
  }
  .desktop-nav {
    display: none;
  }
  .mobile-menu-btn {
    display: inline-flex;
    margin-left: auto;
  }
  .app-main {
    padding: 10px;
  }
}
</style>
