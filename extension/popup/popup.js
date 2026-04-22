import { getState, setState, pushHistory } from "../lib/storage.js";
import { generatePrompt } from "../lib/api.js";
import { awardApproval, levelFromExp, progressInLevel } from "../lib/exp.js";

const PERSONA_META = {
  senior: { emoji: "🧑‍💼", title: "꼼꼼한 사수 박사수" },
  peer:   { emoji: "🧑‍🤝‍🧑", title: "싹싹한 동기 김동기" },
  intern: { emoji: "🧑‍🎓", title: "엉뚱한 인턴 이인턴" }
};

const els = {
  emoji: document.getElementById("mate-emoji"),
  title: document.getElementById("mate-title"),
  badge: document.getElementById("level-badge"),
  expBar: document.getElementById("exp-bar"),
  expText: document.getElementById("exp-text"),
  openOptions: document.getElementById("open-options"),
  input: document.getElementById("user-input"),
  brain: document.getElementById("brain-select"),
  generateBtn: document.getElementById("generate-btn"),
  status: document.getElementById("status"),
  error: document.getElementById("error"),
  card: document.getElementById("result-card"),
  resultText: document.getElementById("result-text"),
  resultMeta: document.getElementById("result-meta"),
  approveBtn: document.getElementById("approve-btn"),
  modal: document.getElementById("levelup-modal"),
  modalTitle: document.getElementById("levelup-title"),
  modalBody: document.getElementById("levelup-body"),
  modalClose: document.getElementById("levelup-close")
};

let state = null;
let lastResult = null;

function paintMate() {
  const meta = PERSONA_META[state.user?.persona] || PERSONA_META.senior;
  els.emoji.textContent = meta.emoji;
  els.title.textContent = state.user?.nickname ? `${state.user.nickname}님의 ${meta.title}` : meta.title;
}

function paintExp() {
  const L = levelFromExp(state.exp);
  const p = progressInLevel(state.exp);
  els.badge.textContent = `Lv.${L.level} ${L.title}`;
  els.expBar.style.width = `${Math.round(p.ratio * 100)}%`;
  els.expText.textContent = p.isMax
    ? `EXP ${state.exp} (만렙)`
    : `EXP ${state.exp} · 다음 승진까지 ${L.max - state.exp + 1}`;
}

function showError(msg) {
  els.error.textContent = msg;
  els.error.classList.remove("hidden");
}
function clearError() { els.error.classList.add("hidden"); }
function showStatus(msg) {
  els.status.textContent = msg;
  els.status.classList.remove("hidden");
}
function clearStatus() { els.status.classList.add("hidden"); }

async function handleGenerate() {
  const text = els.input.value.trim();
  if (!text) {
    showError("어떤 업무가 필요한지 한 줄만 적어주세요.");
    return;
  }
  clearError();
  els.card.classList.add("hidden");
  els.generateBtn.disabled = true;
  showStatus("메이트가 정리하고 있어요…");

  try {
    const data = await generatePrompt({
      backendUrl: state.settings.backendUrl,
      userInput: text,
      persona: state.user.persona,
      brain: els.brain.value,
      provider: state.settings.provider,
      nickname: state.user.nickname
    });
    lastResult = data;
    els.resultText.textContent = data.prompt;
    els.resultMeta.textContent = `${data.meta.provider}/${data.meta.model} · ${data.meta.latency_ms}ms`;
    els.card.classList.remove("hidden");
    clearStatus();
  } catch (e) {
    clearStatus();
    showError(e.message || "생성에 실패했어요.");
  } finally {
    els.generateBtn.disabled = false;
  }
}

async function handleApprove() {
  if (!lastResult?.prompt) return;
  try {
    await navigator.clipboard.writeText(lastResult.prompt);
  } catch (e) {
    showError("클립보드 복사에 실패했어요: " + e.message);
    return;
  }

  const { nextExp, leveledUp, after } = awardApproval(state.exp);
  state = await setState({ exp: nextExp, level: after.level });
  await pushHistory({
    at: new Date().toISOString(),
    persona: state.user.persona,
    snippet: lastResult.prompt.slice(0, 80)
  });
  paintExp();

  els.approveBtn.textContent = "복사 완료 ✓ +20 EXP";
  els.approveBtn.disabled = true;
  setTimeout(() => {
    els.approveBtn.textContent = "👍 결재 완료 (복사)";
    els.approveBtn.disabled = false;
  }, 1800);

  if (leveledUp) {
    els.modalTitle.textContent = `🎉 ${after.title}으로 승진!`;
    els.modalBody.textContent = `${state.user.nickname}님 덕분이에요. 앞으로도 잘 부탁드립니다.`;
    els.modal.classList.remove("hidden");
  }
}

async function init() {
  state = await getState();
  if (!state.user) {
    chrome.tabs.create({ url: chrome.runtime.getURL("onboarding/onboarding.html") });
    window.close();
    return;
  }
  paintMate();
  paintExp();
  els.brain.value = state.settings.brain || "fast";
}

els.generateBtn.addEventListener("click", handleGenerate);
els.approveBtn.addEventListener("click", handleApprove);
els.brain.addEventListener("change", async (e) => {
  state = await setState({ settings: { brain: e.target.value } });
});
els.openOptions.addEventListener("click", () => chrome.runtime.openOptionsPage());
els.modalClose.addEventListener("click", () => els.modal.classList.add("hidden"));

init();
