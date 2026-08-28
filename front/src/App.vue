<script setup>
// 레이아웃 루트이자 DeepSightPanel ↔ ContentArea 중재자
import { ref } from 'vue'
import DeepSightPanel from './components/DeepSightPanel.vue'
import ContentArea from './components/ContentArea.vue'
import { askAgent } from './api/agent'

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

// ContentArea → DeepSightPanel : 질문 전송 시 좌측 목록에 세션 추가 후 agent 호출
// 세션 객체를 직접 갱신하므로, 응답이 늦게 와도 그 세션 화면에만 반영된다.
// (사용자가 도중에 다른 세션을 선택해도 결과가 엉뚱한 곳에 붙지 않는다.)
async function onSubmit(text) {
  const session = panelRef.value.addSession(text)
  activeSession.value = session

  session.status = 'loading'
  session.error = ''

  try {
    const result = await askAgent(text)
    session.answer = result.answer
    session.summary = result.summary
    session.tables = result.tables
    session.charts = result.charts
    session.status = 'done'
  } catch (e) {
    session.error = e.message
    session.status = 'error'
  }
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
