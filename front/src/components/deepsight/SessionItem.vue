<script setup>
// 개별 세션(대화) 항목: 질문 텍스트 · 시간 · 삭제
import IconClose from '../icons/IconClose.vue'

defineProps({
  text: { type: String, required: true },
  time: { type: String, default: '' },
  active: { type: Boolean, default: false }
})

defineEmits(['remove', 'select'])
</script>

<template>
  <div
    class="conv__item"
    :class="{ 'is-active': active }"
    @click="$emit('select')"
  >
    <p class="conv__item-text">{{ text }}</p>
    <div class="conv__item-time">{{ time }}</div>
    <button
      class="conv__item-del"
      type="button"
      aria-label="삭제"
      @click.stop="$emit('remove')"
    >
      <IconClose />
    </button>
  </div>
</template>
