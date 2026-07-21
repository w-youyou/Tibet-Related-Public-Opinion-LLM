import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useKbFilterStore = defineStore('kbFilter', () => {
  const selectedKnowledgeBase = ref(localStorage.getItem('selectedKb') || '')

  function setSelected(id: string) {
    selectedKnowledgeBase.value = id
    localStorage.setItem('selectedKb', id)
  }

  function clear() {
    selectedKnowledgeBase.value = ''
    localStorage.removeItem('selectedKb')
  }

  return { selectedKnowledgeBase, setSelected, clear }
})
