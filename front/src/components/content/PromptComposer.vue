<script setup>
// 가운데 입력 영역
// - 질문을 입력받아 submit 이벤트로 상위 컴포넌트에 전달한다.
// - 입력창은 내용 길이에 맞춰 자동으로 높이가 늘어난다.
import { ref, nextTick } from 'vue'
import IconSend from '../icons/IconSend.vue'

const emit = defineEmits(['submit'])
const prompt = ref('')
const inputRef = ref(null)

// textarea는 내용이 늘어도 기본 높이가 자동으로 줄거나 늘지 않는다.
// 매 입력마다 높이를 다시 계산해 한 줄 질문과 긴 질문을 모두 자연스럽게 처리한다.
function autoResize() {
  const el = inputRef.value
  if (!el) return

  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight}px`
}

function send() {
  const text = prompt.value.trim()
  if (!text) return

  emit('submit', text)
  prompt.value = ''

  // v-model 값이 비워진 다음 높이를 다시 계산해야 입력창이 한 줄로 돌아온다.
  nextTick(autoResize)
}
</script>

<template>
  <div class="composer">
    <!-- Enter는 전송, Shift+Enter는 줄바꿈이다. -->
    <textarea
      ref="inputRef"
      class="composer__input"
      v-model="prompt"
      rows="1"
      placeholder="분석 주제를 입력하세요 (예: 아이폰 18이 디스플레이 시장에 미치는 영향)"
      @input="autoResize"
      @keydown.enter.exact.prevent="send"
    ></textarea>

    <button
      class="composer__send"
      type="button"
      aria-label="전송"
      :disabled="!prompt.trim()"
      @click="send"
    >
      <IconSend />
    </button>
  </div>
</template>
