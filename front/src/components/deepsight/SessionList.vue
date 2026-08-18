<script setup>
// 세션 목록 컨테이너: 세션 배열을 받아 SessionItem 으로 렌더링
import SessionItem from './SessionItem.vue'

defineProps({
  sessions: { type: Array, default: () => [] },
  activeId: { type: [Number, String], default: null }
})

defineEmits(['remove', 'select'])
</script>

<template>
  <div class="conv__list">
    <SessionItem
      v-for="s in sessions"
      :key="s.id"
      :text="s.text"
      :time="s.time"
      :active="s.id === activeId"
      @remove="$emit('remove', s.id)"
      @select="$emit('select', s.id)"
    />
  </div>
</template>
