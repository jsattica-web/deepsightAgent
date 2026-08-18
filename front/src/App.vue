<script setup>
// 레이아웃 루트이자 DeepSightPanel ↔ ContentArea 중재자
import { ref } from 'vue'
import DeepSightPanel from './components/DeepSightPanel.vue'
import ContentArea from './components/ContentArea.vue'

const panelRef = ref(null)
const activeSession = ref(null)

// DeepSightPanel → ContentArea : 새 세션이면 가운데를 빈 히어로로 초기화
function onNewSession() {
  activeSession.value = null
}

// DeepSightPanel → ContentArea : 선택한 세션을 가운데에 표시
function onSelectSession(session) {
  activeSession.value = session
}

// ContentArea → DeepSightPanel : 질문 전송 시 좌측 목록에 세션 추가
function onSubmit(text) {
  activeSession.value = panelRef.value.addSession(text)
}
</script>

<template>
  <div class="app-body">
    <DeepSightPanel
      ref="panelRef"
      @new-session="onNewSession"
      @select-session="onSelectSession"
    />
    <ContentArea :active-session="activeSession" @submit="onSubmit" />
  </div>
</template>
