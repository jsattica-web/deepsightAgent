// agent-python(FastAPI) 호출 모듈
//
// 경로는 반드시 상대경로 '/api/...' 를 쓴다.
// 개발은 vite 프록시가, 운영은 nginx가 '/api' 를 떼고 agent-python으로 넘긴다.
// 절대 URL을 쓰면 오리진이 갈라져 CORS가 발생한다.

// LLM 응답은 수십 초가 걸릴 수 있다. nginx(300s)보다 짧게 잡아 브라우저가 먼저 정리하게 한다.
const TIMEOUT_MS = 120000

/**
 * 응답 본문을 JSON으로 읽는다. 비어 있거나 JSON이 아니면 null을 돌려준다.
 * (nginx가 502/504를 HTML로 내려주는 경우가 있어 방어한다.)
 */
async function readJson(res) {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

/**
 * 자연어 질문을 agent에게 보내고 data 부분을 돌려준다.
 * @param {string} question
 * @returns {Promise<{answer: string, summary: string[], tables: object[], charts: object[]}>}
 */
export async function askAgent(question) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)

  let res
  try {
    res = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal: controller.signal
    })
  } catch (e) {
    // abort와 네트워크 단절을 구분해 사용자에게 다른 안내를 준다.
    if (e.name === 'AbortError') {
      throw new Error('응답이 너무 오래 걸려 중단했습니다. 잠시 후 다시 시도해 주세요.')
    }
    throw new Error('서버에 연결하지 못했습니다. agent 서버가 실행 중인지 확인해 주세요.')
  } finally {
    clearTimeout(timer)
  }

  const body = await readJson(res)

  if (!res.ok) {
    // FastAPI 오류 응답은 message(공통 핸들러) 또는 detail(FastAPI 기본) 을 갖는다.
    const reason = body?.message || body?.detail || `요청이 실패했습니다. (HTTP ${res.status})`
    throw new Error(reason)
  }

  if (!body) {
    throw new Error('서버 응답을 해석하지 못했습니다.')
  }

  // 200이어도 본문 status가 error 일 수 있다.
  if (body.status === 'error') {
    throw new Error(body.message || '요청 처리 중 오류가 발생했습니다.')
  }

  const data = body.data ?? {}
  return {
    answer: data.answer ?? '',
    summary: data.summary ?? [],
    tables: data.tables ?? [],
    charts: data.charts ?? []
  }
}
