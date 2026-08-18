<script setup>
// 가운데 ① 출력 영역
// - 활성 세션이 없으면 히어로 인트로를 보여준다.
// - 활성 세션이 있으면 그 세션의 내용(질문)을 출력한다.
import IconChart from '../icons/IconChart.vue'

defineProps({
  activeSession: { type: Object, default: null }
})
</script>

<template>
  <!-- 활성 세션이 없을 때: 히어로 인트로 -->
  <template v-if="!activeSession">
    <div class="hero__logo"><IconChart /></div>
    <h1 class="hero__title">DeepSight</h1>
    <p class="hero__subtitle">컨설팅 프레임 · ML 수요예측 · AI 보고서 자동 작성</p>
  </template>

  <!-- 활성 세션이 있을 때: 세션 내용 출력 -->
  <div v-else class="hero__thread">
    <div class="msg msg--user">{{ activeSession.text }}</div>
  </div>
</template>
