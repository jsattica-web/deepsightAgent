<script setup>
// 가운데 내용영역 컨테이너
// - 두 영역(SessionDisplay=출력 / PromptComposer=입력)으로 분리되어 있다.
// - DeepSightPanel 과의 상호작용(activeSession prop / submit 이벤트)을 중계한다.
import { ref, watch, nextTick } from 'vue'
import SessionDisplay from './content/SessionDisplay.vue'
import PromptComposer from './content/PromptComposer.vue'

const props = defineProps({
  activeSession: { type: Object, default: null }
})
const emit = defineEmits(['submit'])

// 이 영역이 스크롤 컨테이너다(.hero). 세션을 바꾸면 내용만 갈리고 스크롤 위치는 남아
// 새 답변의 중간부터 보이게 된다. 세션이 바뀔 때마다 맨 위로 되돌린다.
const heroRef = ref(null)

watch(
  () => (props.activeSession ? props.activeSession.id : null),
  () => nextTick(() => heroRef.value?.scrollTo({ top: 0 }))
)

function onSubmit(text) {
  emit('submit', text)
}
</script>

<template>
  <section ref="heroRef" class="hero">
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
