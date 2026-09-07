<script setup>
// 가운데 출력 영역
// - 활성 세션이 없으면 첫 화면용 인트로를 보여준다.
// - 활성 세션이 있으면 사용자의 질문과 agent 응답을 보기 좋은 보고서 형태로 보여준다.
import IconChart from '../icons/IconChart.vue'
import ChartBlock from './ChartBlock.vue'
import DebugPanel from './DebugPanel.vue'

defineProps({
  activeSession: { type: Object, default: null }
})

// 숫자는 자릿수 구분을 넣어 읽기 쉽게 한다. 문자열은 서버가 준 표현을 그대로 유지한다.
function formatCell(value) {
  if (typeof value === 'number') return value.toLocaleString('ko-KR')
  if (value === null || value === undefined) return '-'
  return value
}

// 서버 응답 배열은 비어 있을 수 있다. 화면에서는 비어 있는 섹션을 숨겨 답변 밀도를 높인다.
function hasItems(items) {
  return Array.isArray(items) && items.length > 0
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
    <div class="msg msg--user">
      <span class="msg__label">질문</span>
      <p>{{ activeSession.text }}</p>
    </div>

    <!-- 응답 대기 -->
    <div v-if="activeSession.status === 'loading'" class="msg msg--agent is-loading">
      <div class="loading">
        <span class="loading__ring"></span>
        <div>
          <strong>시장 데이터를 분석하고 있습니다</strong>
          <p>질문 의도에 맞는 지표와 뉴스를 정리하는 중입니다.</p>
        </div>
        <span class="dots"><i>.</i><i>.</i><i>.</i></span>
      </div>
    </div>

    <!-- 오류 -->
    <div v-else-if="activeSession.status === 'error'" class="msg msg--agent msg--error">
      {{ activeSession.error }}
    </div>

    <!-- 정상 응답 -->
    <div v-else-if="activeSession.status === 'done'" class="msg msg--agent">
      <header class="answer__head">
        <div>
          <span class="answer__eyebrow">DeepSight 분석 결과</span>
          <h2 class="answer__title">디스플레이 시장 브리핑</h2>
        </div>
        <span class="answer__status">완료</span>
      </header>

      <!-- 오픈 전 테스트용. 기본은 접혀 있고, 펼치면 agent 응답 원본을 그대로 보여준다.
           아래 정식 렌더링과 대조하는 것이 목적이라 답변보다 위에 둔다.
           공개 시 이 한 줄만 지우면 된다. -->
      <DebugPanel :session="activeSession" />

      <!-- 핵심 요약은 답변 최상단에 배치한다. 사용자가 긴 본문을 읽기 전에 결론을 먼저 볼 수 있다. -->
      <section v-if="hasItems(activeSession.summary)" class="answer__section answer__section--highlight">
        <h3 class="answer__section-title">핵심 요약</h3>
        <ul class="answer__summary">
          <li v-for="(line, i) in activeSession.summary" :key="i">{{ line }}</li>
        </ul>
      </section>

      <!-- 본문은 줄바꿈을 보존한다. agent가 문단을 나눠 준 경우 그대로 읽히게 하기 위함이다. -->
      <section v-if="activeSession.answer" class="answer__section">
        <h3 class="answer__section-title">상세 분석</h3>
        <p class="answer__text">{{ activeSession.answer }}</p>
      </section>

      <!-- 분석 근거/리스크/액션은 의사결정자가 훑어보기 쉽도록 같은 규격의 블록으로 묶는다. -->
      <div
        v-if="hasItems(activeSession.insights) || hasItems(activeSession.risk_signals) || hasItems(activeSession.actions)"
        class="answer__grid"
      >
        <section v-if="hasItems(activeSession.insights)" class="answer__section">
          <h3 class="answer__section-title">분석 근거</h3>
          <ul class="answer__list">
            <li v-for="(line, i) in activeSession.insights" :key="i">{{ line }}</li>
          </ul>
        </section>

        <section v-if="hasItems(activeSession.risk_signals)" class="answer__section">
          <h3 class="answer__section-title">리스크 신호</h3>
          <ul class="answer__list">
            <li v-for="(line, i) in activeSession.risk_signals" :key="i">{{ line }}</li>
          </ul>
        </section>

        <section v-if="hasItems(activeSession.actions)" class="answer__section">
          <h3 class="answer__section-title">권장 조치</h3>
          <ol class="answer__list answer__list--ordered">
            <li v-for="(line, i) in activeSession.actions" :key="i">{{ line }}</li>
          </ol>
        </section>
      </div>

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

      <!-- 차트. 표와 함께 보여준다(라이트 모드에서 일부 색이 대비 기준에 못 미쳐 표가 보조 수단 역할을 한다). -->
      <ChartBlock
        v-for="(chart, ci) in activeSession.charts"
        :key="ci"
        :chart="chart"
      />
    </div>
  </div>
</template>
