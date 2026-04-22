// 서비스 워커. 설치 시 온보딩을 띄우고, 팝업이 닫혀도 계속 돌도록
// 프롬프트 생성 작업을 여기서 수행한다.

import { getState, setState } from "./lib/storage.js";
import { generatePrompt } from "./lib/api.js";

chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === "install") {
    chrome.tabs.create({ url: chrome.runtime.getURL("onboarding/onboarding.html") });
  }
});

chrome.action.onClicked.addListener(async () => {
  // popup이 설정되어 있으므로 보통은 호출되지 않지만, 안전망.
  const state = await getState();
  if (!state.user) {
    chrome.tabs.create({ url: chrome.runtime.getURL("onboarding/onboarding.html") });
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  console.log("[bg] onMessage", message?.type);
  if (message?.type === "GENERATE_PROMPT") {
    // fire-and-forget. 서비스 워커는 fetch가 끝날 때까지 살아있다.
    runGeneration(message.payload);
    sendResponse({ ok: true });
    return false;
  }
});

async function runGeneration(payload) {
  console.log("[bg] runGeneration start", payload);
  const startedAt = new Date().toISOString();
  const state = await setState({
    job: {
      status: "pending",
      input: payload,
      result: null,
      error: null,
      approved: false,
      startedAt,
      finishedAt: null
    }
  });
  console.log("[bg] pending saved. backendUrl=", state.settings.backendUrl);

  try {
    const data = await generatePrompt({
      backendUrl: state.settings.backendUrl,
      userInput: payload.userInput,
      persona: payload.persona,
      brain: payload.brain,
      provider: state.settings.provider,
      nickname: payload.nickname
    });
    console.log("[bg] fetch ok, saving success");
    await setState({
      job: {
        status: "success",
        result: data,
        error: null,
        finishedAt: new Date().toISOString()
      }
    });
    console.log("[bg] success saved");
  } catch (e) {
    console.error("[bg] fetch failed", e);
    await setState({
      job: {
        status: "error",
        result: null,
        error: e?.message || "생성에 실패했어요.",
        finishedAt: new Date().toISOString()
      }
    });
  }
}
