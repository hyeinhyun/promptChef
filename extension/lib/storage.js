// chrome.storage.local 래퍼. 모든 영속 상태는 여기를 통해 다룬다.

const KEY = "officeMate.v1";

const DEFAULT_STATE = {
  user: null,                 // { nickname: string, persona: "senior"|"peer"|"intern", createdAt: ISOString }
  exp: 0,                     // 누적 EXP
  level: 1,                   // 1=수습, 2=대리, 3=팀장
  settings: {
    backendUrl: "http://localhost:8000",
    brain: "fast",            // fast | deep
    provider: null            // null이면 백엔드 기본값 사용
  },
  history: []                 // 최근 5건 {at, persona, snippet}
};

export async function getState() {
  const obj = await chrome.storage.local.get(KEY);
  const stored = obj[KEY] || {};
  return {
    ...DEFAULT_STATE,
    ...stored,
    settings: { ...DEFAULT_STATE.settings, ...(stored.settings || {}) }
  };
}

export async function setState(patch) {
  const current = await getState();
  const next = {
    ...current,
    ...patch,
    settings: { ...current.settings, ...(patch.settings || {}) }
  };
  await chrome.storage.local.set({ [KEY]: next });
  return next;
}

export async function resetState() {
  await chrome.storage.local.remove(KEY);
}

export async function pushHistory(entry) {
  const state = await getState();
  const next = [entry, ...state.history].slice(0, 5);
  await setState({ history: next });
}
