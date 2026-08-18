<script setup>
// 가운데 내용영역 컨테이너
// - 두 영역(SessionDisplay=출력 / PromptComposer=입력)으로 분리되어 있다.
// - DeepSightPanel 과의 상호작용(activeSession prop / submit 이벤트)을 중계한다.
import SessionDisplay from './content/SessionDisplay.vue'
import PromptComposer from './content/PromptComposer.vue'

const props = defineProps({
  activeSession: { type: Object, default: null }
})
const emit = defineEmits(['submit'])

function onSubmit(text) {
  emit('submit', text)
}
</script>

<template>
  <section class="hero">
    <div class="hero__inner">
      <!-- ① 출력 영역 -->
      <SessionDisplay :active-session="activeSession" />

      <!-- ② 입력 영역 (세션이 바뀌면 remount 되어 입력이 초기화됨) -->
      <PromptComposer
        :key="activeSession ? activeSession.id : 'new'"
        @submit="onSubmit"
      />
    </div>
  </section>
</template>
