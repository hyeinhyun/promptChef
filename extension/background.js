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
    // fire-and-forget. keep-alive 루프가 SW 수명을 지켜준다.
    runGeneration(message.payload);
    sendResponse({ ok: true });
    return false;
  }
});

// MV3 서비스 워커는 이벤트 핸들러가 반환된 뒤 30초 idle이면 종료된다.
// fire-and-forget fetch는 이 타이머에 잡히지 않아서, 느린 LLM 응답 중간에
// SW가 죽고 fetch가 abort되는 일이 생긴다. 주기적으로 chrome API를 호출해
// idle 타이머를 리셋한다.
let keepAliveTimer = null;
let keepAliveCount = 0;

function startKeepAlive() {
  if (keepAliveTimer) return;
  keepAliveCount = 0;
  console.log("[bg] keep-alive start");
  keepAliveTimer = setInterval(() => {
    keepAliveCount += 1;
    // 어떤 chrome.* API든 한 번 부르면 idle 타이머가 리셋된다.
    chrome.runtime.getPlatformInfo().then(() => {
      console.log("[bg] keep-alive ping", keepAliveCount);
    }).catch(() => {});
  }, 20_000);
}

function stopKeepAlive() {
  if (!keepAliveTimer) return;
  console.log("[bg] keep-alive stop after", keepAliveCount, "pings");
  clearInterval(keepAliveTimer);
  keepAliveTimer = null;
}

async function runGeneration(payload) {
  console.log("[bg] runGeneration start", payload);
  startKeepAlive();
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
  } finally {
    stopKeepAlive();
  }
}
