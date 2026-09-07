<script setup>
// 좌측 DeepSight 패널
// - 세션 상태를 보유한다.
// - '새 세션 생성'은 별도 컴포넌트가 아닌 이 컴포넌트의 자체 기능(newSession)으로 구현한다.
// - ContentArea 와 상호작용:
//     · new-session / select-session 이벤트를 상위(App)로 방출
//     · addSession()을 노출하여 ContentArea 의 질문 전송 시 세션을 추가한다.
import { ref, reactive, computed, watch } from 'vue'
import { loadSessions, saveSessions, formatTime } from '../storage/sessionStore'
import SessionList from './deepsight/SessionList.vue'
import IconPlus from './icons/IconPlus.vue'
import IconSun from './icons/IconSun.vue'
import IconMoon from './icons/IconMoon.vue'
import IconClose from './icons/IconClose.vue'

// close: 좁은 화면에서 드로어로 열렸을 때 닫기 요청 (여닫는 상태는 App이 들고 있다)
const emit = defineEmits(['new-session', 'select-session', 'close'])

// 테마 토글 (다크 ↔ 라이트). 초기값은 수동 지정값 > OS 설정 순으로 결정한다.
const theme = ref(
  document.documentElement.dataset.theme ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
)
function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
}

// 이전에 저장해 둔 이력으로 시작한다. 없으면 빈 목록이다.
// reactive로 감싸야 App.vue에서 응답을 채울 때 화면이 갱신된다.
const sessions = ref(loadSessions().map((item) => reactive(item)))

// 내용이 바뀔 때마다 저장한다(질문 추가, 응답 도착, 삭제 모두 포함).
watch(sessions, (list) => saveSessions(list.map((item) => ({ ...item }))), { deep: true })

// 목록에 보여줄 시각은 저장된 시각으로부터 매번 계산한다.
// 문자열로 굳혀 두면 다음 날 새로고침해도 '방금'으로 남는다.
const displaySessions = computed(() =>
  sessions.value.map((item) => ({ id: item.id, text: item.text, time: formatTime(item.createdAt) }))
)

const activeId = ref(null)
// 복원된 이력과 id가 겹치지 않게 가장 큰 값 다음부터 발급한다.
let nextId = sessions.value.reduce((max, item) => Math.max(max, Number(item.id) || 0), 100) + 1

// 새 세션 생성 (DeepSightPanel 자체 기능)
// 원본 동작과 동일하게, 목록 항목은 첫 질문 전송 시 추가되고 여기서는 가운데 화면만 초기화한다.
function newSession() {
  activeId.value = null
  emit('new-session')
}

// 세션 선택 → 가운데(ContentArea)에 해당 세션 표시
function selectSession(id) {
  activeId.value = id
  emit('select-session', sessions.value.find((s) => s.id === id))
}

function removeSession(id) {
  sessions.value = sessions.value.filter((s) => s.id !== id)
  if (activeId.value === id) newSession()
}

function clearAll() {
  sessions.value = []
  newSession()
}

// ContentArea 에서 질문을 전송하면 호출된다: 목록 맨 위에 세션을 추가하고 활성화
function addSession(text) {
  // 세션 한 건의 형태를 여기서 한 번에 정의한다.
  // status: 'idle' | 'loading' | 'done' | 'error'
  // reactive로 감싸야 App.vue에서 응답을 채울 때 화면이 갱신된다.
  // (raw 객체를 반환하면 배열 안의 프록시와 달라 변경 알림이 가지 않는다.)
  const session = reactive({
    id: nextId++,
    text,
    createdAt: new Date().toISOString(),
    status: 'idle',
    answer: '',
    summary: [],
    tables: [],
    charts: [],
    insights: [],
    risk_signals: [],
    actions: [],
    error: ''
  })
  sessions.value.unshift(session)
  activeId.value = session.id
  return session
}

defineExpose({ addSession })
</script>

<template>
  <section class="conv">
    <!-- 헤더: 제목 + 새 세션 버튼 (자체 기능) -->
    <div class="conv__head">
      <span class="conv__title">Display 나침반</span>
      <div class="conv__head-actions">
        <button
          class="conv__add"
          type="button"
          :aria-label="theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'"
          @click="toggleTheme"
        >
          <IconSun v-if="theme === 'dark'" />
          <IconMoon v-else />
        </button>
        <button
          class="conv__add"
          type="button"
          aria-label="새 세션"
          @click="newSession"
        >
          <IconPlus />
        </button>
        <!-- 좁은 화면에서 드로어로 열렸을 때만 보인다(CSS) -->
        <button
          class="conv__add conv__close"
          type="button"
          aria-label="이력 닫기"
          @click="emit('close')"
        >
          <IconClose />
        </button>
      </div>
    </div>

    <!-- 세션 목록 (반복 렌더링만 하위 컴포넌트로 분리) -->
    <SessionList
      :sessions="displaySessions"
      :active-id="activeId"
      @select="selectSession"
      @remove="removeSession"
    />

    <!-- 푸터: 전체 삭제 -->
    <div class="conv__foot">
      <button class="conv__clear" type="button" @click="clearAll">전체 삭제</button>
    </div>
  </section>
</template>
