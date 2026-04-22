import { getState, setState, resetState } from "../lib/storage.js";

const els = {
  backendUrl: document.getElementById("backendUrl"),
  provider: document.getElementById("provider"),
  brain: document.getElementById("brain"),
  persona: document.getElementById("persona"),
  save: document.getElementById("save"),
  reset: document.getElementById("reset"),
  status: document.getElementById("status")
};

async function init() {
  const state = await getState();
  els.backendUrl.value = state.settings.backendUrl;
  els.provider.value = state.settings.provider || "";
  els.brain.value = state.settings.brain || "fast";
  els.persona.value = state.user?.persona || "senior";
}

els.save.addEventListener("click", async () => {
  const state = await getState();
  await setState({
    settings: {
      backendUrl: els.backendUrl.value.trim() || "http://localhost:8000",
      provider: els.provider.value || null,
      brain: els.brain.value
    },
    user: state.user
      ? { ...state.user, persona: els.persona.value }
      : { nickname: "", persona: els.persona.value, createdAt: new Date().toISOString() }
  });
  els.status.classList.remove("hidden");
  setTimeout(() => els.status.classList.add("hidden"), 1500);
});

els.reset.addEventListener("click", async () => {
  if (!confirm("EXP·메이트 정보까지 모두 초기화돼요. 진행할까요?")) return;
  await resetState();
  chrome.tabs.create({ url: chrome.runtime.getURL("onboarding/onboarding.html") });
});

init();
