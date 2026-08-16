(() => {
  const results = [];
  function check(name, actual, expected) {
    const passed = actual === expected;
    results.push({ name, passed, actual, expected });
    if (!passed) throw new Error(`${name}: expected ${expected}, received ${actual}`);
  }

  const message = document.querySelector(".message-body").innerText;
  const parsed = LittleAmigosParser.parseMessage(message);
  check("separate first and last name", parsed.name, "Eli Enaz");
  check("post code whitespace", parsed.postcode, "2760");
  check("natural English date", parsed.party_date, "2027-02-20");
  check("email", parsed.email, "customer@example.com");
  check("Australian spaced phone", parsed.phone, "0450 101 795");
  check("Canberra 29 routing", LittleAmigosParser.routePostcode("2912"), "Little Amigos Canberra");
  check("Canberra 26 routing", LittleAmigosParser.routePostcode("2601"), "Little Amigos Canberra");
  check("Southland routing", LittleAmigosParser.routePostcode("3192"), "Little Amigos Southland");
  check("out of area routing", LittleAmigosParser.routePostcode("2000"), "Out of area");
  check(
    "conversation ID",
    LittleAmigosExtractor.conversationId("https://app.zumocrm.com/v2/location/abc/conversations/conversations/conv-123?tab=all"),
    "conv-123"
  );
  check("visible DOM extraction", LittleAmigosExtractor.extractVisibleMessage().includes("First name: Eli"), true);

  const passed = results.filter((result) => result.passed).length;
  document.querySelector("#results").textContent = `${passed}/${results.length} passed\n\n` + results.map((result) => `✓ ${result.name}`).join("\n");
  document.documentElement.dataset.testStatus = passed === results.length ? "passed" : "failed";
})();
