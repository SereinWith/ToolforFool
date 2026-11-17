import { defineStore } from 'pinia'

// 全局 store 占位：后续可存放抓取列表、检索关键词等状态
export const useAppStore = defineStore('app', {
  state: () => ({
    version: '0.1.0'
  })
})
