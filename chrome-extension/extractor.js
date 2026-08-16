(() => {
  // Keep Zumo-specific selectors isolated here so DOM changes require one small update.
  const MESSAGE_SELECTORS = [
    "[data-testid*='message']",
    "[data-testid*='conversation'] [class*='message']",
    "[class*='message-body']",
    "[class*='messageBody']",
    "[class*='conversation'] [class*='bubble']"
  ];
  const REQUIRED_LABELS = /first\s*name|post\s*code|postcode|phone\s*number|email|big day|party\s*date/i;

  function visible(element) {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function extractVisibleMessage() {
    const candidates = [];
    for (const selector of MESSAGE_SELECTORS) {
      for (const element of document.querySelectorAll(selector)) {
        const text = (element.innerText || element.textContent || "").trim();
        if (visible(element) && text.length >= 20 && REQUIRED_LABELS.test(text)) {
          candidates.push(text);
        }
      }
    }
    candidates.sort((a, b) => b.length - a.length);
    return candidates[0] || "";
  }

  function conversationId(url = location.href) {
    const parsed = new URL(url);
    const specific = parsed.pathname.match(/\/conversations\/conversations\/([^/?#]+)/i);
    if (specific) return decodeURIComponent(specific[1]);
    const fallback = parsed.pathname.match(/\/conversations\/([^/?#]+)/i);
    return fallback ? decodeURIComponent(fallback[1]) : "";
  }

  globalThis.LittleAmigosExtractor = { extractVisibleMessage, conversationId, MESSAGE_SELECTORS };
})();
