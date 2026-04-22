import { getState, setState, pushHistory } from "../lib/storage.js";
import { awardApproval, levelFromExp, progressInLevel } from "../lib/exp.js";

const STORAGE_KEY = "officeMate.v1";

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
  modalClose: document.getElementById("levelup-close"),
  personaPopover: document.getElementById("persona-popover"),
  personaOptions: document.querySelectorAll(".persona-option")
};

let state = null;
let lastRenderedJobKey = null;

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

function renderApproveButton(approved) {
  if (approved) {
    els.approveBtn.textContent = "복사 완료 ✓";
    els.approveBtn.disabled = true;
  } else {
    els.approveBtn.textContent = "👍 결재 완료 (복사)";
    els.approveBtn.disabled = false;
  }
}

// 팝업을 다시 열었을 때 state.job 을 보고 UI를 복원한다.
// 처음 로드인지(restore=true) 아니면 실시간 갱신인지에 따라 입력창을 건드릴지 결정한다.
function renderJob(job, { restore = false } = {}) {
  if (!job) job = { status: "idle" };
  const key = `${job.status}:${job.finishedAt || job.startedAt || ""}:${job.approved ? 1 : 0}`;
  if (key === lastRenderedJobKey) return;
  lastRenderedJobKey = key;

  if (job.status === "pending") {
    clearError();
    els.card.classList.add("hidden");
    els.generateBtn.disabled = true;
    showStatus("메이트가 정리하고 있어요…");
    if (restore && job.input?.userInput) els.input.value = job.input.userInput;
    return;
  }
  if (job.status === "success" && job.result) {
    clearStatus();
    clearError();
    els.resultText.textContent = job.result.prompt;
    const m = job.result.meta || {};
    els.resultMeta.textContent = `${m.provider || ""}/${m.model || ""} · ${m.latency_ms ?? ""}ms`;
    els.card.classList.remove("hidden");
    els.generateBtn.disabled = false;
    renderApproveButton(job.approved);
    if (restore && job.input?.userInput) els.input.value = job.input.userInput;
    return;
  }
  if (job.status === "error") {
    clearStatus();
    els.card.classList.add("hidden");
    els.generateBtn.disabled = false;
    showError(job.error || "생성에 실패했어요.");
    if (restore && job.input?.userInput) els.input.value = job.input.userInput;
    return;
  }
  // idle
  clearStatus();
  clearError();
  els.card.classList.add("hidden");
  els.generateBtn.disabled = false;
}

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

  const payload = {
    userInput: text,
    persona: state.user.persona,
    brain: els.brain.value,
    nickname: state.user.nickname
  };

  try {
    const resp = await chrome.runtime.sendMessage({ type: "GENERATE_PROMPT", payload });
    console.log("[popup] sendMessage resp=", resp);
  } catch (e) {
    console.error("[popup] sendMessage failed", e);
    clearStatus();
    showError("백그라운드와 통신에 실패했어요: " + (e?.message || e));
    els.generateBtn.disabled = false;
  }
}

async function handleApprove() {
  const job = state.job;
  if (!job?.result?.prompt || job.status !== "success") return;
  try {
    await navigator.clipboard.writeText(job.result.prompt);
  } catch (e) {
    showError("클립보드 복사에 실패했어요: " + e.message);
    return;
  }

  // 이미 결재한 결과에 중복 EXP를 주지 않는다.
  if (job.approved) {
    renderApproveButton(true);
    return;
  }

  const { nextExp, leveledUp, after } = awardApproval(state.exp);
  state = await setState({
    exp: nextExp,
    level: after.level,
    job: { approved: true }
  });
  await pushHistory({
    at: new Date().toISOString(),
    // 히스토리에는 "이 결과를 만들 때" 쓴 페르소나를 남긴다.
    // 결재 시점엔 이미 다른 페르소나로 바꿨을 수도 있어서 state.user.persona는 부정확.
    persona: job.input?.persona || state.user.persona,
    snippet: job.result.prompt.slice(0, 80)
  });
  paintExp();
  renderApproveButton(true);

  if (leveledUp) {
    els.modalTitle.textContent = `🎉 ${after.title}으로 승진!`;
    els.modalBody.textContent = `${state.user.nickname}님 덕분이에요. 앞으로도 잘 부탁드립니다.`;
    els.modal.classList.remove("hidden");
  }
}

// 팝업이 열려 있는 동안 백그라운드가 job을 갱신하면 반영한다.
// state가 초기화된 뒤에만 등록해야 한다. 팝업이 열리자마자 background가
// storage를 갱신하는 경우가 이 PR의 핵심 시나리오라, state=null 상태에서
// ...state.settings / ...state.job를 평가하면 바로 터진다.
function onStorageChanged(changes, area) {
  if (area !== "local") return;
  const change = changes[STORAGE_KEY];
  if (!change?.newValue) return;
  const next = change.newValue;
  state = {
    ...state,
    ...next,
    settings: { ...state.settings, ...(next.settings || {}) },
    job: { ...state.job, ...(next.job || {}) }
  };
  renderJob(state.job);
}

async function init() {
  state = await getState();
  console.log("[popup] init state.job=", state.job);
  if (!state.user) {
    chrome.tabs.create({ url: chrome.runtime.getURL("onboarding/onboarding.html") });
    window.close();
    return;
  }
  paintMate();
  paintExp();
  els.brain.value = state.settings.brain || "fast";
  renderJob(state.job, { restore: true });
  chrome.storage.onChanged.addListener(onStorageChanged);
}

// ----- 메이트 전환 팝오버 -----
function openPersonaPopover() {
  const current = state?.user?.persona;
  els.personaOptions.forEach((btn) => {
    btn.setAttribute("aria-selected", btn.dataset.persona === current ? "true" : "false");
  });
  els.personaPopover.classList.remove("hidden");
  els.emoji.setAttribute("aria-expanded", "true");
}
function closePersonaPopover() {
  els.personaPopover.classList.add("hidden");
  els.emoji.setAttribute("aria-expanded", "false");
}
function isPersonaPopoverOpen() {
  return !els.personaPopover.classList.contains("hidden");
}

async function handlePersonaPick(persona) {
  if (!state?.user) return;
  if (state.user.persona === persona) {
    closePersonaPopover();
    return;
  }
  // 진행 중인 job의 결과는 이미 고정이므로 건드리지 않는다. 다음 생성부터 새 persona가 적용된다.
  state = await setState({ user: { ...state.user, persona } });
  paintMate();
  closePersonaPopover();
}

els.emoji.addEventListener("click", (e) => {
  e.stopPropagation();
  if (isPersonaPopoverOpen()) closePersonaPopover();
  else openPersonaPopover();
});
els.personaOptions.forEach((btn) => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    handlePersonaPick(btn.dataset.persona);
  });
});
document.addEventListener("click", (e) => {
  if (!isPersonaPopoverOpen()) return;
  if (els.personaPopover.contains(e.target) || els.emoji.contains(e.target)) return;
  closePersonaPopover();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && isPersonaPopoverOpen()) closePersonaPopover();
});

els.generateBtn.addEventListener("click", handleGenerate);
els.approveBtn.addEventListener("click", handleApprove);
els.brain.addEventListener("change", async (e) => {
  state = await setState({ settings: { brain: e.target.value } });
});
els.openOptions.addEventListener("click", () => chrome.runtime.openOptionsPage());
els.modalClose.addEventListener("click", () => els.modal.classList.add("hidden"));

init();
