<script setup>
// 가운데 ① 출력 영역
// - 활성 세션이 없으면 히어로 인트로를 보여준다.
// - 활성 세션이 있으면 질문과 agent 응답(요약/본문/표)을 출력한다.
import IconChart from '../icons/IconChart.vue'
import ChartBlock from './ChartBlock.vue'
import DebugPanel from './DebugPanel.vue'

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
    <h1 class="hero__title">Display 나침반</h1>
    <!-- 팀 크레딧. 역할은 작게, 이름은 또렷하게 두어 대비를 준다. -->
    <ul class="hero__credits">
      <li class="hero__credit">
        <span class="hero__credit-role">기획 및 설계</span>
        <span class="hero__credit-name">김 파트장</span>
      </li>
      <li class="hero__credit">
        <span class="hero__credit-role">화면 및 연계</span>
        <span class="hero__credit-name">박 프로</span>
      </li>
      <li class="hero__credit">
        <span class="hero__credit-role">ToolCalling &amp; Agent</span>
        <span class="hero__credit-name">G최 프로 · J최 프로</span>
      </li>
    </ul>
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
      <!-- 오픈 전 테스트용. 공개 시 이 한 줄만 지우면 된다. -->
      <DebugPanel :session="activeSession" />

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

      <!-- 차트. 표와 함께 보여준다(라이트 모드에서 일부 색이 대비 기준에 못 미쳐
           표가 보조 수단 역할을 한다). -->
      <ChartBlock
        v-for="(chart, ci) in activeSession.charts"
        :key="ci"
        :chart="chart"
      />
    </div>
  </div>
</template>
