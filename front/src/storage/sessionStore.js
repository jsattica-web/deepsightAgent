// 세션 이력을 브라우저 localStorage에 보관한다.
// 새로고침·브라우저 재시작을 견디고, 사용자가 '전체 삭제'를 누르면 함께 비워진다.
//
// 서버가 아니라 브라우저에 저장하므로 기기·브라우저마다 이력이 따로 쌓인다.
// 팀원 간 공유가 필요해지면 backend로 옮겨야 한다.

const STORAGE_KEY = 'display-compass.sessions.v1'

// 응답에 표·차트 원본이 통째로 들어가 한 건이 수십 KB가 된다.
// localStorage는 대략 5MB가 한계라 보관 건수를 제한한다.
const MAX_SESSIONS = 30

/** 저장된 값이 오래됐거나 손상됐을 때를 대비해 필요한 필드를 채워 준다. */
function normalize(raw) {
  return {
    id: raw?.id ?? Date.now(),
    text: raw?.text ?? '',
    createdAt: raw?.createdAt ?? null,
    // 저장 시점에 응답을 기다리던 세션은 되살릴 방법이 없다. 오류로 표시한다.
    status: raw?.status === 'loading' ? 'error' : (raw?.status ?? 'idle'),
    answer: raw?.answer ?? '',
    summary: raw?.summary ?? [],
    tables: raw?.tables ?? [],
    charts: raw?.charts ?? [],
    insights: raw?.insights ?? [],
    risk_signals: raw?.risk_signals ?? [],
    actions: raw?.actions ?? [],
    error:
      raw?.status === 'loading'
        ? '이전에 응답을 받지 못한 질문입니다. 다시 질문해 주세요.'
        : (raw?.error ?? '')
  }
}

/** 저장된 이력을 읽는다. 값이 없거나 깨져 있으면 빈 배열을 돌려준다. */
export function loadSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.map(normalize)
  } catch {
    // 손상된 값이 남아 계속 실패하지 않도록 지운다.
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      /* 저장소 자체를 쓸 수 없는 환경(시크릿 모드 등)은 그냥 넘어간다. */
    }
    return []
  }
}

/** 이력을 저장한다. 용량이 넘치면 오래된 것부터 버리며 재시도한다. */
export function saveSessions(sessions) {
  let candidate = sessions.slice(0, MAX_SESSIONS)

  while (candidate.length > 0) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(candidate))
      return
    } catch {
      // QuotaExceededError. 절반으로 줄여 다시 시도한다.
      candidate = candidate.slice(0, Math.floor(candidate.length / 2))
    }
  }

  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* 저장소를 쓸 수 없는 환경이면 이력 없이 동작한다. */
  }
}

/** 목록에 보여줄 시각 문자열. 같은 날이면 시:분, 아니면 월/일까지 붙인다. */
export function formatTime(createdAt) {
  if (!createdAt) return ''
  const date = new Date(createdAt)
  if (Number.isNaN(date.getTime())) return ''

  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()

  const hm = `${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
  return sameDay ? hm : `${date.getMonth() + 1}/${date.getDate()} ${hm}`
}
