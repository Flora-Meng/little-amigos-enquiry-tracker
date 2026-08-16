const form = document.querySelector("#settings-form");
const trackerUrl = document.querySelector("#tracker-url");
const apiToken = document.querySelector("#api-token");
const statusText = document.querySelector("#status");

chrome.storage.local.get(["trackerUrl", "apiToken"], (stored) => {
  trackerUrl.value = stored.trackerUrl || "http://127.0.0.1:8000";
  apiToken.value = stored.apiToken || "";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = trackerUrl.value.trim().replace(/\/+$/, "");
  const token = apiToken.value.trim();
  let permissionPattern;
  try {
    const parsed = new URL(url);
    permissionPattern = `${parsed.protocol}//${parsed.hostname}/*`;
  } catch { show("Enter a valid Tracker URL.", false); return; }
  const granted = await chrome.permissions.request({ origins: [permissionPattern] });
  if (!granted) { show("Tracker site permission was not granted.", false); return; }
  await chrome.storage.local.set({ trackerUrl: url, apiToken: token });
  const result = await chrome.runtime.sendMessage({ type: "api", path: "/api/zumo/conversations/extension-connection-test/" });
  show(result.ok ? "Connected successfully." : `Connection failed: ${result.data?.error || result.status}`, result.ok);
});

function show(message, success) {
  statusText.textContent = message;
  statusText.className = success ? "success" : "error";
}
