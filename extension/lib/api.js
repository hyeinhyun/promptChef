// 백엔드 API 호출 헬퍼.

export async function generatePrompt({ backendUrl, userInput, persona, brain, provider, nickname }) {
  const url = trimSlash(backendUrl) + "/generate";
  const body = {
    user_input: userInput,
    persona,
    brain,
    nickname: nickname || null
  };
  if (provider) body.provider = provider;

  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  if (!resp.ok) {
    const detail = await safeText(resp);
    throw new Error(`백엔드 오류 (${resp.status}): ${detail || resp.statusText}`);
  }
  return resp.json();
}

export async function fetchPersonas(backendUrl) {
  const url = trimSlash(backendUrl) + "/personas";
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`페르소나 정보를 불러오지 못했습니다 (${resp.status})`);
  return resp.json();
}

function trimSlash(s) {
  return (s || "").replace(/\/+$/, "");
}

async function safeText(resp) {
  try { return await resp.text(); } catch { return ""; }
}
