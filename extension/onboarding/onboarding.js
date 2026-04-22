import { getState, setState } from "../lib/storage.js";
import { fetchPersonas } from "../lib/api.js";

// 백엔드 미응답 대비 기본 페르소나 (백엔드 personas.py와 동기화).
const FALLBACK_PERSONAS = [
  { id: "senior", name: "박사수", title: "꼼꼼한 사수", description: "구조화·팩트 중심·차분한 비즈니스 톤. 보고/기획/분석에 강함.", tone_keywords: ["구조화","근거","단계별","비즈니스"], emoji: "🧑‍💼" },
  { id: "peer",   name: "김동기", title: "싹싹한 동기", description: "쿠션어·정중함·유연한 소통 톤. 메일/요청/협업 메시지에 강함.", tone_keywords: ["정중","협업","쿠션어","공감"], emoji: "🧑‍🤝‍🧑" },
  { id: "intern", name: "이인턴", title: "엉뚱한 인턴", description: "아이디어 발산·트렌디·창의적인 톤. 카피/브레인스토밍/콘텐츠 기획에 강함.", tone_keywords: ["발산","트렌드","창의","에너지"], emoji: "🧑‍🎓" }
];

const grid = document.getElementById("persona-grid");
const nicknameInput = document.getElementById("nickname");
const submitBtn = document.getElementById("submit");
const errorEl = document.getElementById("error");

let personas = FALLBACK_PERSONAS;
let selected = null;

function render() {
  grid.innerHTML = "";
  for (const p of personas) {
    const card = document.createElement("div");
    card.className = "persona-card" + (selected === p.id ? " selected" : "");
    card.dataset.id = p.id;
    card.innerHTML = `
      <div class="persona-emoji mb-2">${p.emoji}</div>
      <div class="font-semibold text-slate-800">${p.title}</div>
      <div class="text-xs text-slate-500 mb-2">${p.name}</div>
      <p class="text-sm text-slate-600 leading-snug">${p.description}</p>
      <div class="mt-2 flex flex-wrap gap-1">
        ${p.tone_keywords.map(k => `<span class="text-[11px] bg-white border border-slate-200 text-slate-500 rounded-full px-2 py-0.5">#${k}</span>`).join("")}
      </div>
    `;
    card.addEventListener("click", () => {
      selected = p.id;
      render();
      updateSubmit();
    });
    grid.appendChild(card);
  }
}

function updateSubmit() {
  const nick = nicknameInput.value.trim();
  submitBtn.disabled = !(nick && selected);
}

async function init() {
  const state = await getState();
  // 이미 온보딩 완료한 사용자는 곧장 옵션 페이지로 보내지 않고 그냥 다시 설정 가능.
  if (state.user?.nickname) nicknameInput.value = state.user.nickname;
  if (state.user?.persona) selected = state.user.persona;

  // 백엔드에서 페르소나 동적 로딩 시도 (실패해도 fallback 유지).
  try {
    const data = await fetchPersonas(state.settings.backendUrl);
    if (data?.personas?.length) personas = data.personas;
  } catch {
    /* 무시 */
  }

  render();
  updateSubmit();
}

nicknameInput.addEventListener("input", updateSubmit);

submitBtn.addEventListener("click", async () => {
  const nickname = nicknameInput.value.trim();
  if (!nickname || !selected) return;
  errorEl.classList.add("hidden");
  submitBtn.disabled = true;

  try {
    await setState({
      user: { nickname, persona: selected, createdAt: new Date().toISOString() }
    });
    // 완료 화면으로 전환.
    document.body.innerHTML = `
      <main class="w-full max-w-md bg-white rounded-2xl shadow-lg p-10 text-center">
        <div class="text-6xl mb-4">🎉</div>
        <h2 class="text-xl font-bold text-slate-800">${nickname}님, 환영합니다!</h2>
        <p class="text-slate-600 mt-2 text-sm">이제 브라우저 우측 상단의 메이트 아이콘을 눌러 시작하세요.</p>
      </main>
    `;
    document.body.className = "bg-slate-50 min-h-screen flex items-center justify-center p-6";
  } catch (e) {
    errorEl.textContent = "저장에 실패했어요: " + e.message;
    errorEl.classList.remove("hidden");
    submitBtn.disabled = false;
  }
});

init();
