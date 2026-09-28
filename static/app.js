const state = {
  mode: "bonus",
  books: [],
  sports: [],
  pollTimer: null,
};

const $ = (id) => document.getElementById(id);

function fmtBook(b) {
  return b.split("_").map((w) => w[0].toUpperCase() + w.slice(1)).join(" ");
}

function americanFmt(n) {
  const v = Number(n);
  return (v > 0 ? "+" : "") + v.toFixed(0);
}

// ---------- init ----------

async function init() {
  const savedKey = localStorage.getItem("bonusHedgeApiKey");
  if (savedKey) $("api-key").value = savedKey;
  $("api-key").addEventListener("change", () => {
    localStorage.setItem("bonusHedgeApiKey", $("api-key").value);
  });

  const res = await fetch("/api/meta");
  if (res.status === 401) return; // browser will show the basic-auth prompt
  const meta = await res.json();

  const cfgBooks = new Set(meta.config.allowed_books || meta.books);
  const cfgSports = new Set(meta.config.sports || meta.sports);

  const bonusSelect = $("bonus-book");
  meta.books.forEach((b) => {
    const opt = document.createElement("option");
    opt.value = b;
    opt.textContent = fmtBook(b);
    bonusSelect.appendChild(opt);
  });

  const sportsList = $("sports-list");
  meta.sports.forEach((s) => {
    sportsList.appendChild(makeCheckbox("sport", s, s.toUpperCase(), cfgSports.has(s)));
  });

  const booksList = $("books-list");
  meta.books.forEach((b) => {
    booksList.appendChild(makeCheckbox("book", b, fmtBook(b), cfgBooks.has(b)));
  });

  $("books-all").addEventListener("click", () => setAllChecked("book", true));
  $("books-none").addEventListener("click", () => setAllChecked("book", false));

  document.querySelectorAll("#mode-toggle .seg").forEach((btn) => {
    btn.addEventListener("click", () => setMode(btn.dataset.mode));
  });

  $("find-btn").addEventListener("click", startSearch);
  $("save-config-btn").addEventListener("click", saveConfig);
  $("m-calc-btn").addEventListener("click", runManualCalc);
}

function makeCheckbox(group, value, label, checked) {
  const wrap = document.createElement("label");
  const input = document.createElement("input");
  input.type = "checkbox";
  input.dataset.group = group;
  input.value = value;
  input.checked = checked;
  wrap.appendChild(input);
  wrap.appendChild(document.createTextNode(label));
  return wrap;
}

function setAllChecked(group, checked) {
  document.querySelectorAll(`input[data-group="${group}"]`).forEach((cb) => (cb.checked = checked));
}

function getChecked(group) {
  return Array.from(document.querySelectorAll(`input[data-group="${group}"]:checked`)).map((cb) => cb.value);
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll("#mode-toggle .seg").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  if (mode === "bonus") {
    $("bonus-book-label").textContent = "Bonus Book";
    $("threshold-label").textContent = "Min Efficiency (%)";
  } else {
    $("bonus-book-label").textContent = "Qualifying Book";
    $("threshold-label").textContent = "Max Loss (%)";
  }
}

// ---------- config ----------

async function saveConfig() {
  const body = { allowed_books: getChecked("book"), sports: getChecked("sport") };
  await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  setStatus("Sports/books saved.");
}

// ---------- manual calculator ----------

async function runManualCalc() {
  const body = {
    stake: parseFloat($("m-stake").value),
    odds_a: parseFloat($("m-odds-a").value),
    odds_b: parseFloat($("m-odds-b").value),
  };
  const res = await fetch("/api/calc", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json();
  if (!res.ok) {
    $("manual-result").textContent = "Error: " + data.error;
    return;
  }
  const b = data.bonus, q = data.qualifying;
  const qLabel = q.loss < 0 ? "Profit" : "Loss";
  $("manual-result").textContent =
    `Bonus:      Hedge $${b.hedge_stake.toFixed(2)}  |  Profit $${b.profit.toFixed(2)}  |  Efficiency ${b.efficiency_pct.toFixed(2)}%\n` +
    `Qualifying: Hedge $${q.hedge_stake.toFixed(2)}  |  ${qLabel} $${Math.abs(q.loss).toFixed(2)}  |  Loss ${q.loss_pct.toFixed(2)}%`;
}

// ---------- search ----------

function setStatus(text) {
  $("status").textContent = text;
}

function setProgress(visible, pct, label) {
  $("progress-wrap").classList.toggle("hidden", !visible);
  $("progress-fill").style.width = pct + "%";
  $("progress-label").textContent = label;
}

async function startSearch() {
  const apiKey = $("api-key").value.trim();
  const bonusBook = $("bonus-book").value;
  const stake = parseFloat($("stake").value);
  const threshold = parseFloat($("threshold").value);
  const sports = getChecked("sport");
  const books = getChecked("book");

  if (!apiKey) return alert("Please enter an API key");
  if (!sports.length) return alert("Select at least one sport");
  if (!books.length) return alert("Select at least one hedge book");

  $("find-btn").disabled = true;
  $("results").textContent = "";
  setStatus("Starting search...");
  setProgress(true, 0, "");

  const body = { mode: state.mode, api_key: apiKey, bonus_book: bonusBook, stake, threshold, sports, books };
  const res = await fetch("/api/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json();

  if (!res.ok) {
    setStatus("");
    setProgress(false, 0, "");
    $("results").innerHTML = `<span class="bad">Error: ${data.error}</span>`;
    $("find-btn").disabled = false;
    return;
  }

  pollJob(data.job_id);
}

function pollJob(jobId) {
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    const res = await fetch(`/api/search/${jobId}`);
    const job = await res.json();

    if (job.progress && job.progress.total) {
      const pct = Math.round((job.progress.current / job.progress.total) * 100);
      setProgress(true, pct, `Fetching ${job.progress.label} odds... (${job.progress.current}/${job.progress.total} - ${pct}%)`);
      setStatus("Searching...");
    }

    if (job.status === "done") {
      clearInterval(state.pollTimer);
      setProgress(false, 100, "");
      $("find-btn").disabled = false;
      renderResults(job.result);
    } else if (job.status === "error") {
      clearInterval(state.pollTimer);
      setProgress(false, 0, "");
      $("find-btn").disabled = false;
      setStatus("Search failed");
      $("results").innerHTML = `<span class="bad">${job.error}</span>`;
    }
  }, 1000);
}

function renderResults(result) {
  const lines = [];
  lines.push(`Analyzed ${result.odds_count} odds entries, ${result.opportunity_count} opportunities found.\n`);

  if (!result.best) {
    setStatus("Search complete - no opportunities found");
    lines.push(result.mode === "bonus" ? "No valid bonus hedge opportunities found." : "No valid qualifying hedge opportunities found.");
    $("results").textContent = lines.join("\n");
    return;
  }

  setStatus(`Search complete - ${result.opportunity_count} opportunities`);
  const best = result.best;

  if (result.mode === "bonus") {
    lines.push("=".repeat(70));
    lines.push("BEST BONUS HEDGE OPPORTUNITY");
    lines.push("=".repeat(70));
    lines.push(`Event: ${best.event}`);
    lines.push(`Bonus (${fmtBook(best.bonus_book)}): ${best.selection} @ ${americanFmt(best.bonus_odds)}`);
    lines.push(`Hedge (${fmtBook(best.hedge_book)}): ${best.opposite} @ ${americanFmt(best.hedge_odds)}  stake $${best.hedge_stake.toFixed(2)}`);
    lines.push(`Locked profit: $${best.profit.toFixed(2)}  |  Efficiency: ${(best.efficiency * 100).toFixed(2)}%`);
    lines.push("=".repeat(70));

    if (result.opportunities.length > 1) {
      lines.push(`\nTop ${result.opportunities.length} opportunities:`);
      result.opportunities.forEach((o, i) => {
        lines.push(`\n#${i + 1}. ${o.event}`);
        lines.push(`   ${fmtBook(o.bonus_book)}: ${o.selection} @ ${americanFmt(o.bonus_odds)} | ${fmtBook(o.hedge_book)}: ${o.opposite} @ ${americanFmt(o.hedge_odds)}`);
        lines.push(`   Hedge: $${o.hedge_stake.toFixed(2)} | Profit: $${o.profit.toFixed(2)} | Efficiency: ${(o.efficiency * 100).toFixed(2)}%`);
      });
    }
  } else {
    const label = best.loss < 0 ? "Guaranteed Profit" : "Guaranteed Loss";
    lines.push("=".repeat(70));
    lines.push("BEST QUALIFYING BET HEDGE");
    lines.push("=".repeat(70));
    lines.push(`Event: ${best.event}`);
    lines.push(`Qualifying (${fmtBook(best.qual_book)}): ${best.selection} @ ${americanFmt(best.qual_odds)}`);
    lines.push(`Hedge (${fmtBook(best.hedge_book)}): ${best.opposite} @ ${americanFmt(best.hedge_odds)}  stake $${best.hedge_stake.toFixed(2)}`);
    lines.push(`${label}: $${Math.abs(best.loss).toFixed(2)}  |  Loss: ${(best.loss_pct * 100).toFixed(2)}% of stake`);
    lines.push("=".repeat(70));

    if (result.opportunities.length > 1) {
      lines.push(`\nTop ${result.opportunities.length} opportunities (sorted by loss):`);
      result.opportunities.forEach((o, i) => {
        const l = o.loss < 0 ? "Profit" : "Loss";
        lines.push(`\n#${i + 1}. ${o.event}`);
        lines.push(`   ${fmtBook(o.qual_book)}: ${o.selection} @ ${americanFmt(o.qual_odds)} | ${fmtBook(o.hedge_book)}: ${o.opposite} @ ${americanFmt(o.hedge_odds)}`);
        lines.push(`   Hedge: $${o.hedge_stake.toFixed(2)} | ${l}: $${Math.abs(o.loss).toFixed(2)} | Loss: ${(o.loss_pct * 100).toFixed(2)}%`);
      });
    }
  }

  $("results").textContent = lines.join("\n");
}

init();
