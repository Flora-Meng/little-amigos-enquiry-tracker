(() => {
  if (globalThis.__littleAmigosImporterLoaded) return;
  globalThis.__littleAmigosImporterLoaded = true;

  const Parser = globalThis.LittleAmigosParser;
  const Extractor = globalThis.LittleAmigosExtractor;
  const host = document.createElement("div");
  host.id = "little-amigos-importer";
  const shadow = host.attachShadow({ mode: "closed" });
  document.documentElement.appendChild(host);

  shadow.innerHTML = `
    <style>
      *{box-sizing:border-box}button,input,textarea,select{font:inherit}.launcher{position:fixed;z-index:2147483646;right:18px;bottom:18px;width:52px;height:52px;border:0;border-radius:17px;background:#f68f6f;color:white;font:800 16px system-ui;box-shadow:0 10px 30px #0003;cursor:pointer}.panel{position:fixed;z-index:2147483647;right:18px;bottom:82px;width:min(390px,calc(100vw - 28px));max-height:calc(100vh - 110px);overflow:auto;border:1px solid #ded9cf;border-radius:20px;background:#fffdf8;color:#21313a;box-shadow:0 18px 50px #0004;font:14px/1.4 system-ui,-apple-system,sans-serif}.hidden{display:none!important}.head{position:sticky;top:0;display:flex;justify-content:space-between;gap:12px;padding:17px 18px;border-bottom:1px solid #e8e4da;background:#fffdf8}.head strong{display:block;font-size:16px}.head span{color:#68777f;font-size:11px}.close{border:0;background:transparent;font-size:22px;cursor:pointer}.body{padding:18px}.state{margin-bottom:15px;padding:10px 12px;border-radius:10px;background:#f1eee7;font-weight:700}.state.ok{background:#ddf4ef;color:#286d61}.state.warn{background:#fff2bf;color:#6e5a16}.notice{margin:12px 0;padding:11px;border-radius:10px;background:#fff2bf;color:#6e5a16}.field{display:grid;gap:5px;margin:11px 0}.field label{font-size:12px;font-weight:750}.field input,.field textarea,.field select{width:100%;padding:9px 10px;border:1px solid #d7d3ca;border-radius:9px;background:white;color:#21313a}.field textarea{min-height:110px;resize:vertical}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.check{display:flex;align-items:center;gap:8px;margin:10px 0}.check input{width:18px;height:18px}.routing{margin:10px 0;color:#68777f}.routing strong{color:#21313a}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:15px}.actions button{min-height:39px;padding:0 13px;border:0;border-radius:9px;font-weight:800;cursor:pointer}.primary{background:#f68f6f;color:white}.quiet{background:#efebe3;color:#21313a}.danger{background:#ffe1db;color:#8f3a30}.matches{margin:8px 0;padding:0;list-style:none}.matches li{padding:7px 0;border-bottom:1px solid #e5d89f}.matches a{color:#21313a;font-weight:750}.error{color:#a33f34}.small{font-size:11px;color:#68777f}@media(max-width:440px){.panel{right:8px;bottom:70px;width:calc(100vw - 16px)}.launcher{right:10px;bottom:10px}.row{grid-template-columns:1fr}}
    </style>
    <button class="launcher" type="button" aria-label="Open Little Amigos importer">LA</button>
    <section class="panel hidden" aria-label="Little Amigos enquiry importer">
      <div class="head"><div><strong>Little Amigos Importer</strong><span class="conversation"></span></div><button class="close" type="button" aria-label="Close">×</button></div>
      <div class="body">
        <div class="state">Checking conversation…</div>
        <div class="reviewed-actions actions hidden"><button class="open-link primary" type="button">Open Tracker enquiry</button><button class="review-again quiet" type="button">Review again</button></div>
        <form class="preview hidden">
          <div class="field"><label>Visible Zumo message</label><textarea name="original_message" placeholder="If automatic extraction misses the message, paste it here."></textarea></div>
          <button class="extract quiet" type="button">Extract and parse again</button>
          <div class="field"><label>Name *</label><input name="name" required></div>
          <div class="row"><div class="field"><label>Phone</label><input name="phone"></div><div class="field"><label>Email</label><input name="email" type="email"></div></div>
          <div class="row"><div class="field"><label>Postcode</label><input name="postcode" inputmode="numeric"></div><div class="field"><label>Party date</label><input name="party_date" type="date"></div></div>
          <label class="check"><input name="party_date_unknown" type="checkbox"> Not sure yet</label>
          <p class="routing">Detected routing: <strong>—</strong></p>
          <div class="field override-field hidden"><label>Out-of-area override</label><select name="override_location"><option value="">Do not import</option><option value="southland">Little Amigos Southland</option><option value="canberra">Little Amigos Canberra</option></select></div>
          <div class="duplicate-box hidden notice"><strong>Possible duplicate</strong><ul class="matches"></ul></div>
          <p class="feedback small" role="status"></p>
          <div class="actions"><button class="import primary" type="submit">Add to Tracker</button><button class="confirm-import danger hidden" type="button">Create anyway</button><button class="ignore quiet" type="button">Ignore</button></div>
        </form>
      </div>
    </section>`;

  const $ = (selector) => shadow.querySelector(selector);
  const panel = $(".panel");
  const form = $(".preview");
  let activeConversation = "";
  let linkedEnquiryUrl = "";

  $(".launcher").addEventListener("click", () => {
    panel.classList.toggle("hidden");
    if (!panel.classList.contains("hidden")) refreshConversation();
  });
  $(".close").addEventListener("click", () => panel.classList.add("hidden"));
  $(".extract").addEventListener("click", () => extractAndParse(true));
  form.addEventListener("submit", (event) => { event.preventDefault(); importEnquiry(false); });
  $(".confirm-import").addEventListener("click", () => importEnquiry(true));
  $(".ignore").addEventListener("click", ignoreConversation);
  $(".review-again").addEventListener("click", reviewAgain);
  $(".open-link").addEventListener("click", () => chrome.runtime.sendMessage({ type: "open-tracker-url", url: linkedEnquiryUrl }));
  form.elements.postcode.addEventListener("input", updateRouting);
  form.elements.party_date_unknown.addEventListener("change", () => {
    if (form.elements.party_date_unknown.checked) form.elements.party_date.value = "";
    form.elements.party_date.disabled = form.elements.party_date_unknown.checked;
  });

  async function api(path, method = "GET", body = null) {
    return chrome.runtime.sendMessage({ type: "api", path, method, body });
  }

  async function refreshConversation() {
    const id = Extractor.conversationId();
    if (!id) {
      activeConversation = "";
      setState("Open a Zumo conversation to review it.", "warn");
      form.classList.add("hidden");
      return;
    }
    activeConversation = id;
    $(".conversation").textContent = `Conversation ${id}`;
    setState("Checking conversation…");
    const result = await api(`/api/zumo/conversations/${encodeURIComponent(id)}/`);
    if (!result?.ok) {
      setState(errorMessage(result), "warn");
      form.classList.add("hidden");
      return;
    }
    linkedEnquiryUrl = result.data.enquiry_url || "";
    $(".reviewed-actions").classList.add("hidden");
    if (result.data.status === "imported") {
      setState("Already imported", "ok");
      $(".reviewed-actions").classList.remove("hidden");
      $(".open-link").classList.remove("hidden");
      $(".review-again").classList.add("hidden");
      form.classList.add("hidden");
    } else if (result.data.status === "ignored") {
      setState("Previously ignored", "warn");
      $(".reviewed-actions").classList.remove("hidden");
      $(".open-link").classList.add("hidden");
      $(".review-again").classList.remove("hidden");
      form.classList.add("hidden");
    } else {
      setState("Not reviewed");
      form.classList.remove("hidden");
      extractAndParse(false);
    }
  }

  function extractAndParse(showFailure) {
    const extracted = Extractor.extractVisibleMessage();
    if (extracted) form.elements.original_message.value = extracted;
    const parsed = Parser.parseMessage(form.elements.original_message.value);
    for (const key of ["name", "phone", "email", "postcode", "party_date"]) {
      if (parsed[key]) form.elements[key].value = parsed[key];
    }
    form.elements.party_date_unknown.checked = parsed.party_date_unknown;
    updateRouting();
    if (!extracted && showFailure) feedback("No matching Zumo message element found. Paste the message above, then parse again.", false);
  }

  function updateRouting() {
    const route = Parser.routePostcode(form.elements.postcode.value);
    $(".routing strong").textContent = route;
    $(".override-field").classList.toggle("hidden", route !== "Out of area");
  }

  function payload() {
    return {
      conversation_id: activeConversation,
      conversation_url: location.href,
      name: form.elements.name.value.trim(),
      phone: form.elements.phone.value.trim(),
      email: form.elements.email.value.trim(),
      postcode: form.elements.postcode.value.trim(),
      party_date: form.elements.party_date.value,
      party_date_unknown: form.elements.party_date_unknown.checked,
      override_location: form.elements.override_location.value,
      original_message: form.elements.original_message.value
    };
  }

  async function importEnquiry(confirmDuplicate) {
    const body = payload();
    body.confirm_duplicate = confirmDuplicate;
    feedback("Checking and importing…", true);
    const result = await api("/api/zumo/import/", "POST", body);
    if (result.ok) {
      linkedEnquiryUrl = result.data.enquiry_url;
      setState("Already imported", "ok");
      form.classList.add("hidden");
      $(".reviewed-actions").classList.remove("hidden");
      $(".open-link").classList.remove("hidden");
      $(".review-again").classList.add("hidden");
      return;
    }
    if (result.status === 409 && result.data.error === "possible_duplicate") {
      showDuplicates(result.data.matches || []);
      feedback("Review the matches, then choose Create anyway if this is a new party enquiry.", false);
      return;
    }
    feedback(errorMessage(result), false);
  }

  function showDuplicates(matches) {
    const list = $(".matches");
    list.replaceChildren();
    for (const match of matches) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = match.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = `${match.name} · ${match.location} · ${match.status}`;
      item.appendChild(link);
      list.appendChild(item);
    }
    $(".duplicate-box").classList.remove("hidden");
    $(".confirm-import").classList.remove("hidden");
  }

  async function ignoreConversation() {
    const body = payload();
    const result = await api("/api/zumo/ignore/", "POST", body);
    if (result.ok) refreshConversation(); else feedback(errorMessage(result), false);
  }

  async function reviewAgain() {
    const result = await api(`/api/zumo/conversations/${encodeURIComponent(activeConversation)}/review-again/`, "POST");
    if (result.ok) refreshConversation(); else setState(errorMessage(result), "warn");
  }

  function setState(message, tone = "") {
    const state = $(".state");
    state.textContent = message;
    state.className = `state ${tone}`;
  }

  function feedback(message, success) {
    const element = $(".feedback");
    element.textContent = message;
    element.className = `feedback small ${success ? "" : "error"}`;
  }

  function errorMessage(result) {
    const error = result?.data?.error;
    if (error === "extension_not_configured") return "Open the extension icon and connect it to the Tracker first.";
    if (error === "out_of_area") return "Out of area. Choose an override location or Ignore.";
    if (error === "contact_required") return "Enter at least a phone number or email.";
    if (error === "already_reviewed") return "This conversation has already been reviewed. Refreshing status…";
    if (error === "authentication_required") return "The extension token is missing, invalid or revoked.";
    return result?.data?.message || error || "Could not connect to the Tracker.";
  }

  let previousUrl = location.href;
  setInterval(() => {
    if (location.href !== previousUrl) {
      previousUrl = location.href;
      if (!panel.classList.contains("hidden")) refreshConversation();
    }
  }, 1000);
})();
