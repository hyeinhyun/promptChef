// 서비스 워커. 설치 시 온보딩 페이지를 한 번 띄운다.

import { getState } from "./lib/storage.js";

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
