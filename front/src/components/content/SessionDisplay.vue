<script setup>
// 가운데 ① 출력 영역
// - 활성 세션이 없으면 히어로 인트로를 보여준다.
// - 활성 세션이 있으면 질문과 agent 응답(요약/본문/표)을 출력한다.
import IconChart from '../icons/IconChart.vue'

defineProps({
  activeSession: { type: Object, default: null }
})

// 숫자는 자릿수 구분을 넣어 읽기 쉽게 한다. 문자열은 그대로 둔다.
function formatCell(value) {
  if (typeof value === 'number') return value.toLocaleString('ko-KR')
  if (value === null || value === undefined) return '-'
  return value
}
</script>

<template>
  <!-- 활성 세션이 없을 때: 히어로 인트로 -->
  <template v-if="!activeSession">
    <div class="hero__logo"><IconChart /></div>
    <h1 class="hero__title">DeepSight</h1>
    <p class="hero__subtitle">컨설팅 프레임 · ML 수요예측 · AI 보고서 자동 작성</p>
  </template>

  <!-- 활성 세션이 있을 때: 질문 + 응답 출력 -->
  <div v-else class="hero__thread">
    <div class="msg msg--user">{{ activeSession.text }}</div>

    <!-- 응답 대기 -->
    <div v-if="activeSession.status === 'loading'" class="msg msg--agent is-loading">
      분석 중입니다<span class="dots"><i>.</i><i>.</i><i>.</i></span>
    </div>

    <!-- 오류 -->
    <div v-else-if="activeSession.status === 'error'" class="msg msg--agent msg--error">
      {{ activeSession.error }}
    </div>

    <!-- 정상 응답 -->
    <div v-else-if="activeSession.status === 'done'" class="msg msg--agent">
      <!-- 요약 -->
      <ul v-if="activeSession.summary.length" class="answer__summary">
        <li v-for="(line, i) in activeSession.summary" :key="i">{{ line }}</li>
      </ul>

      <!-- 본문 -->
      <p v-if="activeSession.answer" class="answer__text">{{ activeSession.answer }}</p>

      <!-- 표 -->
      <div v-for="(table, ti) in activeSession.tables" :key="ti" class="answer__table-wrap">
        <h3 v-if="table.title" class="answer__table-title">{{ table.title }}</h3>
        <table class="answer__table">
          <thead>
            <tr>
              <th v-for="col in table.columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in table.rows" :key="ri">
              <td v-for="(cell, ci) in row" :key="ci">{{ formatCell(cell) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 차트는 아직 그리지 않는다. 라이브러리 도입 전까지 데이터가 왔다는 사실만 알린다. -->
      <p v-if="activeSession.charts.length" class="answer__note">
        차트 데이터 {{ activeSession.charts.length }}건이 함께 도착했습니다. (그래프 렌더링 미구현)
      </p>
    </div>
  </div>
</template>
