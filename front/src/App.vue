<script setup>
// 레이아웃 루트이자 DeepSightPanel ↔ ContentArea 중재자
import { ref, onMounted, onUnmounted } from 'vue'
import DeepSightPanel from './components/DeepSightPanel.vue'
import ContentArea from './components/ContentArea.vue'
import IconMenu from './components/icons/IconMenu.vue'
import { askAgent } from './api/agent'

const panelRef = ref(null)
const activeSession = ref(null)

// 좁은 화면(모바일/태블릿)에서 좌측 이력은 상시 노출이 아니라 햄버거로 여는 드로어다.
// 넓은 화면에서는 CSS가 항상 펼친 상태로 두므로 이 값은 무시된다.
const panelOpen = ref(false)

function togglePanel() {
  panelOpen.value = !panelOpen.value
}
function closePanel() {
  panelOpen.value = false
}

// 드로어가 화면을 덮고 있으므로 Esc로도 닫을 수 있어야 한다.
function onKeydown(e) {
  if (e.key === 'Escape') closePanel()
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

// DeepSightPanel → ContentArea : 새 세션이면 가운데를 빈 히어로로 초기화
function onNewSession() {
  activeSession.value = null
  closePanel() // 좁은 화면: 고르고 나면 본문이 보이도록 드로어를 닫는다
}

// DeepSightPanel → ContentArea : 선택한 세션을 가운데에 표시
function onSelectSession(session) {
  activeSession.value = session
  closePanel()
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
    session.insights = result.insights
    session.risk_signals = result.risk_signals
    session.actions = result.actions
    session.status = 'done'
  } catch (e) {
    session.error = e.message
    session.status = 'error'
  }
}
</script>

<template>
  <div class="app-body">
    <!-- 햄버거: 좁은 화면에서만 보인다(CSS). 넓은 화면에서는 이력이 항상 펼쳐져 있어 필요 없다. -->
    <button
      class="panel-toggle"
      type="button"
      :aria-label="panelOpen ? '이력 닫기' : '이력 열기'"
      :aria-expanded="panelOpen"
      @click="togglePanel"
    >
      <IconMenu />
    </button>

    <!-- 드로어 뒤 배경. 눌러서 닫는다. -->
    <div v-if="panelOpen" class="panel-backdrop" @click="closePanel"></div>

    <DeepSightPanel
      ref="panelRef"
      :class="{ 'is-open': panelOpen }"
      @new-session="onNewSession"
      @select-session="onSelectSession"
      @close="closePanel"
    />
    <ContentArea :active-session="activeSession" @submit="onSubmit" />
  </div>
</template>
