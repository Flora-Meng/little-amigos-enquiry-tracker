(() => {
  const MONTHS = {
    january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
    july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
    jan: 1, feb: 2, mar: 3, apr: 4, jun: 6, jul: 7, aug: 8, sep: 9, sept: 9, oct: 10, nov: 11, dec: 12
  };

  function field(text, labels) {
    for (const label of labels) {
      const pattern = new RegExp(`(?:^|\\n)\\s*${label}\\s*[:\\-]\\s*([^\\n]+)`, "i");
      const match = text.match(pattern);
      if (match) return match[1].trim();
    }
    return "";
  }

  function isoDate(value) {
    if (!value) return "";
    const clean = value.replace(/(st|nd|rd|th)\b/gi, "").trim();
    let match = clean.match(/^(\d{1,2})[\s/\-]+([A-Za-z]+|\d{1,2})[\s,/\-]+(\d{4})$/);
    if (!match) return "";
    const day = Number(match[1]);
    const month = /^\d+$/.test(match[2]) ? Number(match[2]) : MONTHS[match[2].toLowerCase()];
    const year = Number(match[3]);
    if (!month || month > 12 || day < 1 || day > 31) return "";
    return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  function parseMessage(text) {
    const source = String(text || "").replace(/\r\n?/g, "\n");
    const firstName = field(source, ["First\\s*name"]);
    const lastName = field(source, ["Last\\s*name"]);
    const fullName = field(source, ["Full\\s*name", "Name"]);
    const rawDate = field(source, ["When is the big day\\?\\s*\\(Approximate date\\)", "Party\\s*date", "Approximate\\s*date"]);
    return {
      name: fullName || [firstName, lastName].filter(Boolean).join(" "),
      postcode: field(source, ["Post\\s*code", "Postcode"]),
      party_date: isoDate(rawDate),
      party_date_unknown: /not sure|unknown|tbc|to be confirmed/i.test(rawDate),
      email: field(source, ["Email(?: address)?"]),
      phone: field(source, ["Phone(?: number)?", "Mobile(?: number)?"]),
      original_message: source.trim()
    };
  }

  function routePostcode(value) {
    const postcode = String(value || "").replace(/\D/g, "");
    if (postcode.startsWith("3")) return "Little Amigos Southland";
    if (postcode.startsWith("26") || postcode.startsWith("29")) return "Little Amigos Canberra";
    return "Out of area";
  }

  globalThis.LittleAmigosParser = { parseMessage, routePostcode, isoDate };
})();
