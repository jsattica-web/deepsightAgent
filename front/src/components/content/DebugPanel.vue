<script setup>
// 오픈 전 테스트용 패널.
// agent 응답의 7개 필드를 가공 없이 그대로 보여준다.
// 아래쪽 정식 렌더링(요약/본문/표/차트)과 대조해 확인하는 것이 목적이다.
//
// 공개 전에는 이 컴포넌트를 SessionDisplay에서 빼면 된다.
import { ref } from 'vue'

const props = defineProps({
  session: { type: Object, required: true }
})

// 기본은 접어 둔다. 답변을 먼저 보고, 필요할 때만 펼쳐서 원본을 확인한다.
const open = ref(false)

// 서버 필드명을 그대로 라벨로 쓴다. 응답과 1:1로 맞춰 보기 위함이다.
const FIELDS = [
  { key: 'answer', note: '본문' },
  { key: 'summary', note: '요약' },
  { key: 'insights', note: '분석 근거' },
  { key: 'risk_signals', note: '리스크 신호' },
  { key: 'actions', note: '권장 조치' },
  { key: 'tables', note: '표 데이터' },
  { key: 'charts', note: '차트 데이터' }
]

function valueOf(key) {
  return props.session[key]
}

function isEmpty(v) {
  if (v == null) return true
  if (Array.isArray(v)) return v.length === 0
  if (typeof v === 'string') return v.trim() === ''
  return false
}

// 문자열 배열은 목록으로, 그 외(객체 배열 등)는 JSON 원문으로 보여준다.
function isStringList(v) {
  return Array.isArray(v) && v.every((item) => typeof item === 'string')
}

function countOf(v) {
  if (Array.isArray(v)) return `${v.length}건`
  if (typeof v === 'string') return `${v.length}자`
  return ''
}

function pretty(v) {
  return JSON.stringify(v, null, 2)
}
</script>

<template>
  <section class="debug">
    <header class="debug__head">
      <span class="debug__badge">TEST</span>
      <h3 class="debug__title">agent 응답 원본</h3>
      <button class="debug__toggle" type="button" @click="open = !open">
        {{ open ? '접기' : '펼치기' }}
      </button>
    </header>

    <div v-if="open" class="debug__body">
      <div v-for="field in FIELDS" :key="field.key" class="debug__field">
        <div class="debug__label">
          <code class="debug__key">{{ field.key }}</code>
          <span class="debug__note">{{ field.note }}</span>
          <span class="debug__count">{{ countOf(valueOf(field.key)) }}</span>
        </div>

        <p v-if="isEmpty(valueOf(field.key))" class="debug__empty">(비어 있음)</p>

        <ul v-else-if="isStringList(valueOf(field.key))" class="debug__list">
          <li v-for="(line, i) in valueOf(field.key)" :key="i">{{ line }}</li>
        </ul>

        <p v-else-if="typeof valueOf(field.key) === 'string'" class="debug__text">
          {{ valueOf(field.key) }}
        </p>

        <pre v-else class="debug__json">{{ pretty(valueOf(field.key)) }}</pre>
      </div>
    </div>
  </section>
</template>
