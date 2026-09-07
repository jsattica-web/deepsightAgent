<script setup>
// agent 응답의 charts 항목 하나를 그린다.
//
// 핵심 규칙: 이중 축(y축 2개)은 쓰지 않는다.
// 두 축의 교차 지점은 작성자가 임의로 정하는 값이라, 눈금만 바꿔도
// "함께 움직인다 / 엇갈린다"로 해석이 뒤집힌다. 없는 상관관계를 만들어낸다.
// 대신 자릿수가 10배 넘게 차이 나는 시리즈는 차트를 나눠 각자의 축에 그린다.
import { ref, computed, onMounted, onBeforeUpdate, onBeforeUnmount, watch, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  chart: { type: Object, required: true }
})

// 검증된 카테고리 팔레트. 라이트/다크는 같은 색상환을 각 배경에 맞게 단계만 다르게 잡은 것이다.
// (색각 이상 분리도 ΔE 9.1 light / 8.4 dark 통과)
const SERIES_COLORS = {
  light: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'],
  dark: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']
}

const theme = ref('dark')
// v-for의 :ref 콜백은 인덱스에 채워 넣기만 한다. 그룹 수가 줄면 옛 canvas가 남으므로
// 매 렌더 직전에 비운다. 그리기에만 쓰는 값이라 반응형으로 둘 필요는 없다.
const canvasEls = []
let instances = []
let observer = null

function currentTheme() {
  const stamped = document.documentElement.dataset.theme
  if (stamped) return stamped
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

/**
 * 자릿수가 비슷한 시리즈끼리 묶는다. 그룹 안의 최대값 비율이 10배를 넘으면 축을 나눈다.
 * 색상은 그룹 순서가 아니라 원본 순서로 정한다 (같은 시리즈는 언제나 같은 색).
 */
const groups = computed(() => {
  const datasets = (props.chart.datasets ?? []).map((ds, index) => ({
    label: ds.label,
    data: (ds.data ?? []).map((v) => (typeof v === 'number' ? v : Number(v) || 0)),
    index
  }))

  const withMax = datasets.map((ds) => ({
    ...ds,
    max: ds.data.length ? Math.max(...ds.data.map((v) => Math.abs(v))) : 0
  }))

  // 큰 값부터 훑으면서, 직전 그룹과 10배 안쪽이면 같은 축에 태운다.
  const sorted = [...withMax].sort((a, b) => b.max - a.max)
  const result = []
  for (const ds of sorted) {
    const last = result[result.length - 1]
    if (last && ds.max > 0 && last.max / ds.max <= 10) last.items.push(ds)
    else result.push({ max: ds.max, items: [ds] })
  }
  return result
})

const compact = new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 })
const full = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 })

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function buildCharts() {
  destroyCharts()

  const palette = SERIES_COLORS[theme.value] ?? SERIES_COLORS.dark
  const ink = cssVar('--text-muted', '#9e9e9e')
  const grid = cssVar('--border-soft', 'rgba(255,255,255,0.08)')
  const isBar = props.chart.type === 'bar'

  groups.value.forEach((group, gi) => {
    const canvas = canvasEls[gi]
    if (!canvas) return

    const datasets = group.items.map((ds) => {
      const color = palette[ds.index % palette.length]
      return {
        label: ds.label,
        data: ds.data,
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        // 선은 실제 값을 잇는다. 곡선 보간은 없는 중간값을 있는 것처럼 보이게 한다.
        tension: 0,
        pointRadius: 4,
        pointHoverRadius: 6,
        borderRadius: isBar ? 4 : 0,
        maxBarThickness: 44
      }
    })

    instances.push(
      new Chart(canvas, {
        type: isBar ? 'bar' : 'line',
        data: { labels: props.chart.labels ?? [], datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            // 시리즈가 하나면 범례를 두지 않는다. 캡션이 이미 이름을 말하고 있다.
            legend: {
              display: datasets.length > 1,
              position: 'bottom',
              labels: { color: ink, boxWidth: 10, boxHeight: 10, usePointStyle: true, padding: 14 }
            },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${full.format(ctx.parsed.y)}`
              }
            }
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: ink, font: { size: 11 } },
              border: { color: grid }
            },
            y: {
              grid: { color: grid },
              ticks: { color: ink, font: { size: 11 }, callback: (v) => compact.format(v) },
              border: { display: false }
            }
          }
        }
      })
    )
  })
}

function destroyCharts() {
  instances.forEach((c) => c.destroy())
  instances = []
}

onMounted(() => {
  theme.value = currentTheme()
  nextTick(buildCharts)

  // 테마 토글은 html 요소의 data-theme을 바꾼다. 바뀌면 색을 다시 골라 그린다.
  observer = new MutationObserver(() => {
    const next = currentTheme()
    if (next !== theme.value) theme.value = next
  })
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})

onBeforeUpdate(() => {
  canvasEls.length = 0
})

// 좌측 이력에서 다른 세션을 고르면 SessionDisplay가 이 컴포넌트를 재사용하고 prop만 갈아끼운다.
// canvas는 Chart.js 인스턴스가 쥐고 있어 저절로 바뀌지 않으므로, chart가 바뀌면 다시 그린다.
// (테마 토글도 같은 이유로 다시 그린다.)
watch([theme, () => props.chart], () => nextTick(buildCharts))

onBeforeUnmount(() => {
  observer?.disconnect()
  destroyCharts()
})
</script>

<template>
  <div class="chart">
    <h3 v-if="chart.title" class="chart__title">{{ chart.title }}</h3>

    <div v-for="(group, gi) in groups" :key="gi" class="chart__panel">
      <!-- 축을 나눈 경우에만 어떤 시리즈인지 밝혀 준다 -->
      <p v-if="groups.length > 1" class="chart__caption">
        {{ group.items.map((i) => i.label).join(' · ') }}
      </p>
      <div class="chart__canvas-wrap">
        <canvas :ref="(el) => (canvasEls[gi] = el)"></canvas>
      </div>
    </div>

    <p v-if="groups.length > 1" class="chart__note">
      값의 자릿수가 크게 달라 축을 나눠 그렸습니다.
    </p>
  </div>
</template>
