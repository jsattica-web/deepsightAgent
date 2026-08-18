<script setup>
// 가운데 ② 입력 영역
// - 사용자의 입력을 받고 툴바 컨트롤/전송 버튼을 제공한다.
// - 전송 시 submit 이벤트로 입력 텍스트를 상위(ContentArea)에 올려보낸다.
import { ref, onMounted, onUnmounted } from 'vue'
import IconChevronDown from '../icons/IconChevronDown.vue'
import IconComment from '../icons/IconComment.vue'
import IconSparkle from '../icons/IconSparkle.vue'
import IconSend from '../icons/IconSend.vue'

// mode-change: 모드(일반/딥사이트) 선택 시 방출하는 빈 이벤트 (확장성용 훅)
const emit = defineEmits(['submit', 'mode-change'])

const prompt = ref('')

// 1. 모델 선택 드롭다운 --------------------------------------------------
const models = [
  { text: 'gpt-5.5', value: 'gpt-5.5' },
  { text: 'gpt-4.0', value: 'gpt-4.0' },
  { text: 'gpt-4o', value: 'gpt-4o' },
  { text: 'o3', value: 'o3' }
]
const selectedModel = ref(models[0]) // { text, value }
const modelOpen = ref(false)
const modelRef = ref(null)

function toggleModel() {
  modelOpen.value = !modelOpen.value
}
function selectModel(model) {
  selectedModel.value = model
  modelOpen.value = false
}
// 바깥 영역 클릭 시 드롭다운 닫기
function onDocClick(e) {
  if (modelRef.value && !modelRef.value.contains(e.target)) {
    modelOpen.value = false
  }
}
onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))

// 2. 모드 라디오 (일반 / 딥사이트) — 하나만 선택 --------------------------
const mode = ref('general') // 'general' | 'deep'
function selectMode(next) {
  if (mode.value === next) return
  mode.value = next
  emit('mode-change') // 확장성을 고려한 빈 이벤트
}

// 3. 소스 체크박스 (다중 선택) — list 로 보관 ---------------------------
const sourceOptions = ['웹', '내부데이터', '내부문서', '예측']
const selectedSources = ref([]) // 예: ['웹', '내부데이터']
function toggleSource(source) {
  const idx = selectedSources.value.indexOf(source)
  if (idx === -1) selectedSources.value.push(source)
  else selectedSources.value.splice(idx, 1)
}

function send() {
  const text = prompt.value.trim()
  if (!text) return
  emit('submit', text)
  prompt.value = ''
}
</script>

<template>
  <div class="composer">
    <textarea
      class="composer__input"
      v-model="prompt"
      rows="1"
      placeholder="분석 주제를 입력하세요 (예: 아이폰 18이 디스플레이 시장에 미치는 영향)"
      @keydown.enter.exact.prevent="send"
    ></textarea>

    <div class="composer__toolbar">
      <!-- 1. 모델 드롭다운 -->
      <div ref="modelRef" class="model-select">
        <button class="tool" type="button" @click="toggleModel">
          <IconChevronDown />
          <span>{{ selectedModel.text }}</span>
        </button>
        <ul v-if="modelOpen" class="model-menu">
          <li v-for="m in models" :key="m.value">
            <button
              class="model-option"
              :class="{ 'is-selected': m.value === selectedModel.value }"
              type="button"
              @click="selectModel(m)"
            >
              {{ m.text }}
            </button>
          </li>
        </ul>
      </div>

      <!-- 2. 모드 라디오 (일반 / 딥사이트) -->
      <button
        class="tool"
        :class="{ 'tool--active': mode === 'general' }"
        type="button"
        @click="selectMode('general')"
      >
        <IconComment />
        <span>일반</span>
      </button>

      <button
        class="tool"
        :class="{ 'tool--deep': mode === 'deep' }"
        type="button"
        @click="selectMode('deep')"
      >
        <IconSparkle />
        <span>딥사이트</span>
      </button>

      <!-- 3. 소스 체크박스 (다중 선택) -->
      <button
        v-for="source in sourceOptions"
        :key="source"
        class="tool tool--chip"
        :class="{ 'is-on': selectedSources.includes(source) }"
        type="button"
        @click="toggleSource(source)"
      >
        {{ source }}
      </button>

      <span class="composer__spacer"></span>

      <button
        class="composer__send"
        type="button"
        aria-label="전송"
        @click="send"
      >
        <IconSend />
      </button>
    </div>
  </div>
</template>
