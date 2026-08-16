const ALLOWED_PATHS = [
  /^\/api\/zumo\/conversations\/[^/]+\/$/,
  /^\/api\/zumo\/conversations\/[^/]+\/review-again\/$/,
  /^\/api\/zumo\/(import|ignore)\/$/,
  /^\/api\/zumo\/duplicates\/(?:\?.*)?$/
];

async function settings() {
  const stored = await chrome.storage.local.get(["trackerUrl", "apiToken"]);
  return {
    trackerUrl: String(stored.trackerUrl || "").replace(/\/+$/, ""),
    apiToken: String(stored.apiToken || "")
  };
}

async function apiRequest(message) {
  const config = await settings();
  if (!config.trackerUrl || !config.apiToken) {
    return { ok: false, status: 0, data: { error: "extension_not_configured" } };
  }
  if (!ALLOWED_PATHS.some((pattern) => pattern.test(message.path))) {
    return { ok: false, status: 400, data: { error: "path_not_allowed" } };
  }
  const response = await fetch(`${config.trackerUrl}${message.path}`, {
    method: message.method || "GET",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      "Authorization": `Bearer ${config.apiToken}`
    },
    body: message.body ? JSON.stringify(message.body) : undefined,
    credentials: "omit"
  });
  let data;
  try { data = await response.json(); } catch { data = { error: "invalid_server_response" }; }
  return { ok: response.ok, status: response.status, data };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "api") {
    apiRequest(message).then(sendResponse).catch((error) => {
      sendResponse({ ok: false, status: 0, data: { error: "network_error", message: error.message } });
    });
    return true;
  }
  if (message?.type === "open-tracker-url") {
    settings().then((config) => {
      if (message.url?.startsWith(`${config.trackerUrl}/`)) chrome.tabs.create({ url: message.url });
    });
  }
});
