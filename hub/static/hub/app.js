(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>").replace(/\n/g, "<br>");
  const post = (url, body) =>
    fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": EL.csrf }, body: JSON.stringify(body || {}) })
      .then((r) => r.json());
  const toast = (t) => { const d = document.createElement("div"); d.className = "toast"; d.textContent = t; document.body.append(d); setTimeout(() => d.remove(), 1600); };
  const store = { get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} } };

  // mobile nav
  $("#burger")?.addEventListener("click", () => $("#links").classList.toggle("open"));

  // live AI search suggestions
  const ns = $("#navsearch"), sg = $("#suggest"); let t;
  ns?.addEventListener("input", () => {
    clearTimeout(t);
    if (ns.value.trim().length < 3) { sg.hidden = true; return; }
    t = setTimeout(async () => {
      const d = await fetch("/api/search/?q=" + encodeURIComponent(ns.value)).then((r) => r.json());
      sg.innerHTML = d.results.map((r) => `<a href="${r.url}">${esc(r.title)}<small>${esc(r.board)} · ${r.score}% match</small></a>`).join("") || "<a>No match</a>";
      sg.hidden = false;
    }, 250);
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search")) sg && (sg.hidden = true); });

  // tabs
  $$("#tabs button").forEach((b) => b.addEventListener("click", () => {
    $$("#tabs button").forEach((x) => x.classList.toggle("on", x === b));
    $$(".pane").forEach((p) => p.classList.toggle("on", p.id === b.dataset.tab));
    history.replaceState(null, "", "#" + b.dataset.tab);
  }));
  if (location.hash && $(`#tabs [data-tab="${location.hash.slice(1)}"]`)) $(`#tabs [data-tab="${location.hash.slice(1)}"]`).click();

  // video: load iframe on click (privacy-friendly, fast)
  const v = $("#video");
  const playVideo = () => {
    v.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${v.dataset.id}?autoplay=1&rel=0" title="Project video" allow="accelerometer; autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>`;
    v.onclick = null;
  };
  v?.addEventListener("click", playVideo);
  v?.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && playVideo());

  // syntax highlight (CDN, optional)
  window.addEventListener("load", () => window.hljs && $$("pre code").forEach((c) => hljs.highlightElement(c)));

  // copy / explain
  $$(".code").forEach((box) => {
    const code = () => $("code", box).textContent;
    $(".copy", box).addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(code()); } catch {
        const ta = document.createElement("textarea"); ta.value = code(); document.body.append(ta); ta.select(); document.execCommand("copy"); ta.remove();
      }
      toast("Code copied ✓");
    });
    $(".xplain", box).addEventListener("click", async (e) => {
      const out = $("div.explain", box), btn = e.currentTarget;
      out.hidden = false; out.innerHTML = "<span class='dots'><span></span><span></span><span></span></span> Analysing…"; btn.disabled = true;
      const d = await post(`/api/ai/explain/${box.dataset.file}/`);
      btn.disabled = false;
      out.innerHTML = `<b>${esc(d.summary)}</b><span class="tag-engine">${d.engine}</span>` +
        (d.llm ? `<p>${md(d.llm)}</p>` : "") +
        `<table>${d.notes.map((n) => `<tr><td>L${n.line}</td><td><code>${esc(n.code)}</code>${md(n.text)}</td></tr>`).join("")}</table>`;
    });
  });

  // favourites + print
  const fav = $("#favBtn");
  if (fav) {
    const sync = () => { const on = store.get("fav", []).includes(fav.dataset.slug); fav.textContent = on ? "★ Saved" : "☆ Save"; };
    fav.addEventListener("click", () => { let f = store.get("fav", []); f = f.includes(fav.dataset.slug) ? f.filter((x) => x !== fav.dataset.slug) : [...f, fav.dataset.slug]; store.set("fav", f); sync(); });
    sync();
    $("#printBtn").addEventListener("click", () => window.print());
  }
  // parts checklist persistence
  $$(".chk").forEach((c, i) => {
    const k = "chk-" + EL.project + i; c.checked = store.get(k, false);
    c.addEventListener("change", () => store.set(k, c.checked));
  });

  // troubleshooter (detail + AI lab)
  $("#tsGo")?.addEventListener("click", async () => {
    const out = $("#tsOut"), problem = $("#tsText").value.trim();
    if (!problem) return;
    out.innerHTML = "<span class='dots'><span></span><span></span><span></span></span>";
    const d = await post("/api/ai/troubleshoot/", { problem, project: $("#tsProj")?.value || EL.project });
    out.innerHTML = (d.llm ? `<div class="diag"><h4>AI diagnosis</h4>${md(d.llm)}</div>` : "") +
      d.matches.map((m) => `<div class="diag"><h4>${esc(m.title)}</h4><ul>${m.tips.map((t) => `<li>${esc(t)}</li>`).join("")}</ul></div>`).join("");
  });

  // part finder
  $("#rcGo")?.addEventListener("click", async () => {
    const out = $("#rcOut"), parts = $("#rcText").value.trim();
    if (!parts) return;
    const d = await post("/api/ai/recommend/", { parts });
    out.innerHTML = d.results.length ? d.results.map((r) => `<a class="res" href="${r.url}">${r.thumb ? `<img src="${r.thumb}" alt="">` : ""}<div style="flex:1"><b>${esc(r.title)}</b>
      <div class="bar"><i style="width:${r.score}%"></i></div><small><span class="hit">You have ${r.have.length}</span>${r.missing.length ? ` · <span class="miss">Missing: ${esc(r.missing.join(", "))}</span>` : " · ready to build!"}</small></div><b>${r.score}%</b></a>`).join("")
      : "<p class='muted'>No overlap found — try names like ESP32, Arduino Uno, LED, relay…</p>";
  });

  // semantic search (AI lab)
  const ss = $("#ssText"); let st;
  ss?.addEventListener("input", () => {
    clearTimeout(st);
    st = setTimeout(async () => {
      if (ss.value.trim().length < 3) return;
      const d = await fetch("/api/search/?q=" + encodeURIComponent(ss.value)).then((r) => r.json());
      $("#ssOut").innerHTML = d.results.map((r) => `<a class="res" href="${r.url}"><div style="flex:1"><b>${esc(r.title)}</b><small>${esc(r.summary)}</small></div><b>${r.score}%</b></a>`).join("") || "<p class='muted'>No match.</p>";
    }, 300);
  });

  // chat widget
  const chat = $("#chat"), msgs = $("#chatMsgs"), input = $("#chatInput"); let chatHist = store.get("chat", []);
  const add = (cls, html) => { const d = document.createElement("div"); d.className = "m " + cls; d.innerHTML = html; msgs.append(d); msgs.scrollTop = msgs.scrollHeight; return d; };
  const chipsFor = EL.project ? ["How do I wire it?", "What parts do I need?", "How do I upload the code?"] : ["Best beginner project?", "Which project uses a camera?", "How do I measure distance?"];
  $("#chatChips").innerHTML = chipsFor.map((c) => `<button class="chip" type="button">${c}</button>`).join("");
  if (!chatHist.length) chatHist = [{ role: "assistant", content: "Hi! I'm ElectroLab AI. Ask about wiring, parts, code or troubleshooting." }];
  chatHist.forEach((m) => add(m.role === "user" ? "u" : "b", md(m.content)));
  const openChat = (q) => { chat.hidden = false; input.focus(); if (q) send(q); };
  async function send(q) {
    add("u", esc(q)); chatHist.push({ role: "user", content: q });
    const wait = add("b", "<span class='dots'><span></span><span></span><span></span></span>");
    try {
      const d = await post("/api/ai/chat/", { message: q, project: EL.project, history: chatHist.slice(0, -1) });
      wait.innerHTML = md(d.answer || d.error) + (d.related?.length ? "<br><br>" + d.related.map((r) => `<a href="${r.url}">→ ${esc(r.title)}</a>`).join("<br>") : "");
      chatHist.push({ role: "assistant", content: d.answer || "" });
    } catch { wait.textContent = "Network error — try again."; }
    store.set("chat", chatHist.slice(-20));
  }
  $("#chatFab").addEventListener("click", () => (chat.hidden = !chat.hidden));
  $("#chatClose").addEventListener("click", () => (chat.hidden = true));
  $("#openChat")?.addEventListener("click", () => openChat());
  $("#chatForm").addEventListener("submit", (e) => { e.preventDefault(); const q = input.value.trim(); if (q) { input.value = ""; send(q); } });
  $$(".chip", $("#chatChips")).forEach((c) => c.addEventListener("click", () => send(c.textContent)));
  $$(".qchips .chip").forEach((c) => c.addEventListener("click", () => openChat(c.textContent)));
})();
