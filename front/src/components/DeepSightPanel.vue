<script setup>
// 좌측 DeepSight 패널
// - 세션 상태를 보유한다.
// - '새 세션 생성'은 별도 컴포넌트가 아닌 이 컴포넌트의 자체 기능(newSession)으로 구현한다.
// - ContentArea 와 상호작용:
//     · new-session / select-session 이벤트를 상위(App)로 방출
//     · addSession()을 노출하여 ContentArea 의 질문 전송 시 세션을 추가한다.
import { ref } from 'vue'
import SessionList from './deepsight/SessionList.vue'
import IconPlus from './icons/IconPlus.vue'
import IconSun from './icons/IconSun.vue'
import IconMoon from './icons/IconMoon.vue'

const emit = defineEmits(['new-session', 'select-session'])

// 테마 토글 (다크 ↔ 라이트). 초기값은 수동 지정값 > OS 설정 순으로 결정한다.
const theme = ref(
  document.documentElement.dataset.theme ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
)
function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
}

const sessions = ref([
  { id: 1, text: '아이폰 18이 디스플레이 시장에 미치는 영향 알려줘', time: '7/14 20:32' },
  { id: 2, text: '아이폰 사용자와 갤럭시 사용자간의 전체 인구수 차이는 어떻게 돼?', time: '7/14 18:38' },
  {
    id: 3,
    text: '미국과 이란 전쟁이 지속되고 있는데 이로인한 디스플레이 시장에 미치는 영향을 판매 관점에서 알려줘',
    time: '7/14 16:46'
  }
])

const activeId = ref(null)
let nextId = 100

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
  const session = { id: nextId++, text, time: '방금' }
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
      <span class="conv__title">DeepSight</span>
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
      </div>
    </div>

    <!-- 세션 목록 (반복 렌더링만 하위 컴포넌트로 분리) -->
    <SessionList
      :sessions="sessions"
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
