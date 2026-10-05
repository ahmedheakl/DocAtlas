(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  /* ------------------------------------------------------------------ data (tables of the paper) */
  const LEADERBOARD = [
    { type: "General", name: "Gemini-2.0-Pro", params: "-", text: 0.090, teds: 68.50, formula: 0.356, order: 0.050, overall: 79.75 },
    { type: "General", name: "GPT4o", params: "-", text: 0.117, teds: 62.26, formula: 0.425, order: 0.065, overall: 75.30 },
    { type: "General", name: "Qwen3-VL", params: "3B", text: 0.081, teds: 51.86, formula: 0.420, order: 0.089, overall: 71.87 },
    { type: "General", name: "Qwen2.5-VL", params: "2B", text: 0.174, teds: 50.59, formula: 0.453, order: 0.117, overall: 66.59 },
    { type: "General", name: "InternVL3.5", params: "2B", text: 0.095, teds: 70.80, formula: 0.543, order: 0.060, overall: 77.20 },
    { type: "Expert", name: "DotsOCR", params: "3B", text: 0.068, teds: 65.40, formula: 0.321, order: 0.037, overall: 79.29 },
    { type: "Expert", name: "PaddleOCR-VL", params: "1B", text: 0.078, teds: 73.90, formula: 0.241, order: 0.052, overall: 80.10 },
    { type: "Expert", name: "DeepseekOCR", params: "3B", text: 0.082, teds: 71.54, formula: 0.242, order: 0.053, overall: 81.66 },
    { type: "Expert", name: "MonkeyOCR-pro", params: "1.2B", text: 0.095, teds: 72.80, formula: 0.295, order: 0.065, overall: 78.25 },
    { type: "Expert", name: "Dolphin", params: "400M", text: 0.160, teds: 58.30, formula: 0.465, order: 0.066, overall: 71.17 },
    { type: "Expert", name: "Nanonets-OCR-s", params: "4B", text: 0.088, teds: 71.90, formula: 0.518, order: 0.059, overall: 81.53 },
    { type: "Expert", name: "Nanonets-OCR2", params: "3B", text: 0.088, teds: 66.24, formula: 0.471, order: 0.060, overall: 78.70 },
    { type: "Expert", name: "Chandra", params: "9B", text: 0.071, teds: 69.79, formula: 0.262, order: 0.042, overall: 81.33 },
    { type: "Expert", name: "MinerU2.5", params: "1.2B", text: 0.267, teds: 72.79, formula: 0.273, order: 0.096, overall: 73.07 },
    { type: "Expert", name: "DocAtlas-Deepseek", params: "3B", text: 0.055, teds: 72.24, formula: 0.237, order: 0.049, overall: 83.37, ours: true },
  ];
  const BENCHMARKS = [
    { name: "PubTabNet", year: 2019, langs: 1, cov: [0, 0, 0, 1, 0, 0] },
    { name: "XFUND", year: 2022, langs: 7, cov: [0, 0, 1, 0, 0, 0] },
    { name: "Nougat", year: 2023, langs: 1, cov: [1, 0, 1, 1, 1, 0] },
    { name: "READOC", year: 2025, langs: 27, cov: [1, 1, 1, 1, 1, 0] },
    { name: "OmniDocBench", year: 2025, langs: 2, cov: [1, 1, 1, 1, 1, 0] },
    { name: "DocAtlas", year: 2025, langs: 82, cov: [1, 1, 1, 1, 1, 1], ours: true },
  ];
  const FUNNEL = [
    { stage: "Raw URLs extracted", count: 11.4, label: "11.4M", note: "three Common Crawl snapshots" },
    { stage: "After deduplication", count: 3.4, label: "3.4M", note: "60–80% removed per snapshot" },
    { stage: "Valid HTTP responses", count: 2.44, label: "2.44M", note: "dead links, timeouts" },
    { stage: "After safety filtering", count: 1.9, label: "1.9M", note: "content-type mismatches, malware" },
    { stage: "After parsing and rendering", count: 1.0, label: "1.0M", note: "corrupt archives, short documents" },
  ];
  const CHART_TYPES = [
    { name: "Gemini-2.5-flash", v: [0.471, 0.662, 0.673] },
    { name: "Nanonets-OCR2", v: [0.397, 0.603, 0.446] },
    { name: "DeepseekOCR", v: [0.195, 0.649, 0.522] },
    { name: "GPT-4o", v: [0.280, 0.405, 0.566] },
    { name: "SmolDocling", v: [0.127, 0.038, 0.337] },
  ];
  const ADAPT = [
    { model: "DeepseekOCR", rows: [["Baseline", 81.7, 75.9], ["Full-page SFT", 86.4, 65.8], ["Component SFT", 87.3, 54.6], ["DPO", 83.6, 77.7]] },
    { model: "Nanonets-OCR", rows: [["Baseline", 81.5, 75.7], ["Full-page SFT", 86.3, 65.7], ["Component SFT", 87.1, 54.5], ["DPO", 83.4, 77.6]] },
    { model: "DotsOCR", rows: [["Baseline", 79.3, 73.7], ["Full-page SFT", 83.9, 63.9], ["Component SFT", 84.7, 53.0], ["DPO", 81.1, 75.4]] },
    { model: "Qwen2.5-VL", rows: [["Baseline", 66.6, 61.9], ["Full-page SFT", 70.5, 53.6], ["Component SFT", 71.2, 44.5], ["DPO", 68.1, 63.3]] },
  ];
  const LORA = [
    { name: "Full SFT", full: "Full SFT, all modules", base: -12.1, gain: 13.6 },
    { name: "All layers", full: "LoRA, all layers", base: -5.6, gain: 8.9 },
    { name: "MLP only", full: "LoRA, MLP only", base: -3.9, gain: 10.1 },
    { name: "MLP gate + down", full: "LoRA, MLP gate and down", base: -2.7, gain: 10.8 },
    { name: "All QKV", full: "LoRA, all QKV", base: -1.9, gain: 9.7 },
    { name: "QKV only", full: "LoRA, QKV only", base: 1.3, gain: 9.2, best: true },
  ];
  const SIGNAL = [
    { name: "Baseline (no DPO)", inD: 81.7, outD: 75.9 },
    { name: "GPT-4o distillation", inD: 82.1, outD: 75.2 },
    { name: "DocAtlas ground truth", inD: 83.6, outD: 77.7, best: true },
  ];
  const GROUPS = {
    text: ["Text", "var(--g-text)"], heading: ["Heading", "var(--g-heading)"], table: ["Table", "var(--g-table)"], list: ["List item", "var(--g-list)"],
    picture: ["Picture", "var(--g-picture)"], furniture: ["Page header / footer", "var(--g-furniture)"], caption: ["Caption", "var(--g-caption)"], formula: ["Formula", "var(--g-formula)"],
  };

  /* ------------------------------------------------------------------ helpers */
  const NS = "http://www.w3.org/2000/svg";
  function el(tag, attrs = {}, text) {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function chart(host, w, h, label) {
    host.innerHTML = "";
    const svg = el("svg", { viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": label });
    host.appendChild(svg);
    return svg;
  }
  const tip = $("#tooltip");
  function showTip(evt, html, color) {
    tip.innerHTML = html;
    tip.style.setProperty("--c", color || "var(--amber-2)");
    const pad = 14, r = tip.getBoundingClientRect();
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + r.width > innerWidth - 8) x = evt.clientX - r.width - pad;
    if (y + r.height > innerHeight - 8) y = evt.clientY - r.height - pad;
    tip.style.left = `${Math.max(8, x)}px`;
    tip.style.top = `${Math.max(8, y)}px`;
    tip.classList.add("show");
  }
  const hideTip = () => tip.classList.remove("show");
  function onVisible(node, fn, margin = "0px 0px -12% 0px") {
    if (!("IntersectionObserver" in window)) return fn();
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { io.disconnect(); fn(); }
    }, { rootMargin: margin });
    io.observe(node);
  }

  /* ------------------------------------------------------------------ navigation, reveal, counters */
  function chrome() {
    const nav = $("#nav");
    const bar = $("#progress");
    const onScroll = () => {
      nav.classList.toggle("scrolled", scrollY > 24);
      const max = document.documentElement.scrollHeight - innerHeight;
      if (bar) bar.style.width = `${max > 0 ? Math.min(100, (scrollY / max) * 100) : 0}%`;
    };
    addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    const links = $$(".nav-links a");
    const byId = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        for (const e of entries) if (e.isIntersecting && byId.has(e.target.id)) {
          links.forEach((a) => a.classList.remove("active"));
          byId.get(e.target.id).classList.add("active");
        }
      }, { rootMargin: "-45% 0px -50% 0px" });
      byId.forEach((_, id) => { const s = document.getElementById(id); if (s) io.observe(s); });
    }
    $$(".reveal").forEach((node) => (reduceMotion ? node.classList.add("in") : onVisible(node, () => node.classList.add("in"), "0px 0px -8% 0px")));
    $$("[data-count]").forEach((node) => {
      const target = parseFloat(node.dataset.count), decimals = +(node.dataset.decimals || 0), suffix = node.dataset.suffix || "";
      const show = (v) => (node.textContent = v.toFixed(decimals) + suffix);
      if (reduceMotion) return show(target);
      show(0);
      onVisible(node, () => {
        const t0 = performance.now(), dur = 1500;
        const step = (t) => {
          const p = Math.min(1, (t - t0) / dur);
          show(target * (1 - Math.pow(1 - p, 3)));
          if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }, "0px");
    });
  }

  /* ------------------------------------------------------------------ hero: a globe of scripts */
  function globe() {
    const canvas = $("#globe");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const pool = "A ß ñ ø ç Ž Ж я Ю ѣ Ω λ π ع ش ق ب ی א ש ל अ क ह ज অ ক த அ అ ക ස ก ษ ខ ກ မ ქ ა Ա ք አ ሀ ጸ 字 文 書 語 あ カ 한 글 ગ ਗ ề ğ".split(" ");
    const probe = document.createElement("canvas");
    probe.width = probe.height = 28;
    const pctx = probe.getContext("2d", { willReadFrequently: true });
    const signature = (ch) => {
      pctx.clearRect(0, 0, 28, 28);
      pctx.font = "20px sans-serif"; pctx.textAlign = "center"; pctx.textBaseline = "middle";
      pctx.fillText(ch, 14, 14);
      const d = pctx.getImageData(0, 0, 28, 28).data;
      let s = "";
      for (let i = 3; i < d.length; i += 16) s += d[i] > 40 ? "1" : "0";
      return s;
    };
    const missing = new Set([signature("￿"), signature("͸"), signature(" ")]);
    const glyphs = pool.filter((g) => !missing.has(signature(g)));
    if (!glyphs.length) return;

    const N = 280, golden = Math.PI * (3 - Math.sqrt(5));
    const points = Array.from({ length: N }, (_, i) => {
      const y = 1 - (2 * (i + 0.5)) / N, r = Math.sqrt(1 - y * y), phi = i * golden;
      return { x: Math.cos(phi) * r, y, z: Math.sin(phi) * r, g: glyphs[(i * 7) % glyphs.length], accent: i % 9 === 0, s: 0.8 + ((i * 37) % 10) / 16 };
    });
    let w = 0, h = 0, dpr = 1, tiltX = 0.42, targetX = 0, targetY = 0, mx = 0, my = 0, visible = true, last = 0, angle = 0;
    const resize = () => {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(2, devicePixelRatio || 1);
      w = r.width; h = r.height;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const draw = (t) => {
      if (!visible) return;
      const dt = last ? Math.min(60, t - last) : 16;
      last = t;
      angle += dt * 0.00011;
      mx += (targetX - mx) * 0.04; my += (targetY - my) * 0.04;
      const R = Math.min(w, h) * 0.41, cx = w / 2, cy = h / 2;
      const ay = angle + mx * 0.5, ax = tiltX + my * 0.3;
      const cosY = Math.cos(ay), sinY = Math.sin(ay), cosX = Math.cos(ax), sinX = Math.sin(ax);
      ctx.clearRect(0, 0, w, h);
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(148, 170, 255, .16)";
      ctx.beginPath(); ctx.arc(cx, cy, R * 1.06, 0, Math.PI * 2); ctx.stroke();
      for (let k = 0; k < 6; k++) {                    // meridians
        ctx.beginPath();
        for (let j = 0; j <= 48; j++) {
          const lat = (j / 48) * Math.PI - Math.PI / 2, lon = (k / 6) * Math.PI;
          let x = Math.cos(lat) * Math.cos(lon), y = Math.sin(lat), z = Math.cos(lat) * Math.sin(lon);
          const x1 = x * cosY + z * sinY, z1 = -x * sinY + z * cosY, y1 = y * cosX - z1 * sinX;
          j ? ctx.lineTo(cx + x1 * R, cy + y1 * R) : ctx.moveTo(cx + x1 * R, cy + y1 * R);
        }
        ctx.strokeStyle = "rgba(148, 170, 255, .07)";
        ctx.stroke();
      }
      const proj = points.map((p) => {
        const x1 = p.x * cosY + p.z * sinY, z1 = -p.x * sinY + p.z * cosY;
        const y1 = p.y * cosX - z1 * sinX, z2 = p.y * sinX + z1 * cosX;
        return { p, x: cx + x1 * R, y: cy + y1 * R, z: z2 };
      }).sort((a, b) => a.z - b.z);
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      for (const q of proj) {
        const depth = (q.z + 1) / 2, alpha = 0.06 + 0.9 * Math.pow(depth, 2.2);
        const size = (9 + 17 * depth) * q.p.s * (R / 300);
        ctx.font = `600 ${size.toFixed(1)}px "Noto Sans", system-ui, sans-serif`;
        ctx.fillStyle = q.p.accent ? `rgba(251, 191, 36, ${alpha})` : `rgba(214, 226, 255, ${alpha * 0.92})`;
        ctx.fillText(q.p.g, q.x, q.y);
      }
      if (!reduceMotion) requestAnimationFrame(draw);
    };
    resize();
    addEventListener("resize", () => { resize(); if (reduceMotion) draw(0); });
    addEventListener("pointermove", (e) => { targetX = e.clientX / innerWidth - 0.5; targetY = e.clientY / innerHeight - 0.5; }, { passive: true });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((entries) => {
        const now = entries[0].isIntersecting;
        if (now && !visible) { visible = true; last = 0; requestAnimationFrame(draw); }
        visible = now;
      }).observe(canvas);
    }
    requestAnimationFrame(draw);
  }

  /* ------------------------------------------------------------------ corpus */
  function funnel() {
    const host = $("#funnel");
    if (!host) return;
    const max = FUNNEL[0].count;
    host.innerHTML = FUNNEL.map((f) => {
      const pct = (f.count / max) * 100;
      return `
      <div class="funnel-row">
        <div class="funnel-label"><b>${esc(f.stage)}</b><span>${esc(f.note)}</span></div>
        <div class="funnel-bar"><i data-w="${pct.toFixed(1)}"></i><em${pct < 20 ? ` class="out" style="left:calc(${pct.toFixed(1)}% + 10px)"` : ""}>${f.label}</em></div>
      </div>`;
    }).join("");
    const grow = () => $$("i", host).forEach((bar, i) => setTimeout(() => (bar.style.width = `${bar.dataset.w}%`), reduceMotion ? 0 : 120 * i));
    onVisible(host, grow);
  }
  function matrix() {
    const body = $("#matrix-body");
    if (!body) return;
    body.innerHTML = BENCHMARKS.map((b) => `
      <tr class="${b.ours ? "ours" : ""}">
        <td>${esc(b.name)}</td><td>${b.year}</td>
        <td class="left"><div class="langbar"><i data-w="${Math.max(2, (b.langs / 82) * 150).toFixed(0)}" style="width:${reduceMotion ? Math.max(2, (b.langs / 82) * 150).toFixed(0) : 0}px"></i><span>${b.langs}</span></div></td>
        ${b.cov.map((c) => `<td class="${c ? "yes" : "no"}"><span class="hidden">${c ? "yes" : "no"}</span></td>`).join("")}
      </tr>`).join("");
    onVisible(body, () => $$(".langbar i", body).forEach((bar) => (bar.style.width = `${bar.dataset.w}px`)));
  }

  /* ------------------------------------------------------------------ benchmark explorer */
  async function explorer() {
    const root = $("#explorer");
    if (!root) return;
    let data;
    try {
      data = await (await fetch("assets/examples.json")).json();
    } catch (err) {
      root.classList.add("hidden");
      return;
    }
    const chips = $("#lang-chips"), img = $("#page-img"), page = $("#page"), boxes = $("#boxes"), legend = $("#legend"), meta = $("#meta");
    const paneMd = $("#tab-markdown"), paneTags = $("#tab-doctags"), toggle = $("#toggle-boxes");
    const hiddenGroups = new Set();

    const highlight = (raw) => esc(raw).replace(/&lt;(\/?)([a-z_0-9]+)&gt;/g, (m, slash, name) => {
      const cls = name.startsWith("loc_") ? "l" : /^(fcel|ecel|lcel|ucel|xcel|ched|rhed|srow|nl)$/.test(name) ? "o" : "t";
      return `<span class="${cls}">&lt;${slash}${name}&gt;</span>`;
    });
    const applyGroups = () => {
      $$(".box", boxes).forEach((b) => b.classList.toggle("hidden", hiddenGroups.has(b.dataset.group)));
      $$("button", legend).forEach((b) => b.classList.toggle("off", hiddenGroups.has(b.dataset.group)));
    };
    function select(i) {
      const e = data[i];
      $$(".chip", chips).forEach((c, j) => { c.classList.toggle("active", i === j); c.setAttribute("aria-selected", i === j); });
      page.classList.add("loading");
      img.onload = () => page.classList.remove("loading");
      img.width = e.width; img.height = e.height;
      img.alt = `Benchmark page in ${e.language}`;
      img.src = `assets/examples/${e.slug}.webp`;
      hiddenGroups.clear();
      boxes.innerHTML = "";
      const counts = {};
      e.elements.forEach((item) => {
        counts[item.group] = (counts[item.group] || 0) + 1;
        const node = document.createElement("div");
        node.className = "box";
        node.dataset.group = item.group;
        node.style.cssText = `left:${item.box[0]}%;top:${item.box[1]}%;width:${item.box[2]}%;height:${item.box[3]}%;--c:${GROUPS[item.group][1]}`;
        node.addEventListener("pointermove", (evt) => showTip(evt, `<b>&lt;${esc(item.tag)}&gt;</b>${esc(item.text || "(no text)")}`, GROUPS[item.group][1]));
        node.addEventListener("pointerleave", hideTip);
        boxes.appendChild(node);
      });
      legend.innerHTML = Object.keys(GROUPS).filter((g) => counts[g]).map((g) => `<button data-group="${g}" style="--c:${GROUPS[g][1]}" aria-pressed="true"><i></i>${GROUPS[g][0]} · ${counts[g]}</button>`).join("");
      meta.innerHTML = `<div><span>Language</span><b>${esc(e.language)}</b></div><div><span>Script</span><b>${esc(e.script)}</b></div><div><span>Source</span><b>${esc(e.source)}</b></div><div><span>Elements</span><b>${e.elements.length}</b></div>`;
      paneMd.lang = e.code;
      paneMd.innerHTML = e.markdown;
      paneTags.innerHTML = highlight(e.doctags);
      paneMd.scrollTop = paneTags.scrollTop = 0;
    }
    chips.innerHTML = data.map((e) => `<button class="chip" role="tab"><b>${esc(e.language)}</b><span>${esc(e.script)}</span></button>`).join("");
    $$(".chip", chips).forEach((c, i) => c.addEventListener("click", () => select(i)));
    legend.addEventListener("click", (evt) => {
      const b = evt.target.closest("button");
      if (!b) return;
      hiddenGroups.has(b.dataset.group) ? hiddenGroups.delete(b.dataset.group) : hiddenGroups.add(b.dataset.group);
      applyGroups();
    });
    toggle.addEventListener("change", () => boxes.classList.toggle("off", !toggle.checked));
    $$(".side .tab", root).forEach((t) => t.addEventListener("click", () => {
      $$(".side .tab", root).forEach((x) => x.classList.toggle("active", x === t));
      paneMd.classList.toggle("hidden", t.dataset.tab !== "markdown");
      paneTags.classList.toggle("hidden", t.dataset.tab !== "doctags");
    }));
    select(0);
  }

  /* ------------------------------------------------------------------ leaderboard */
  function leaderboard() {
    const table = $("#leader");
    if (!table) return;
    const body = $("tbody", table), heads = $$("th[data-key]", table);
    const state = { key: "overall", dir: "desc", filter: "all" };
    const size = (p) => (p === "-" ? NaN : parseFloat(p) * (p.endsWith("M") ? 1e6 : 1e9));
    const lowerBetter = { text: true, formula: true, order: true };
    function render() {
      let rows = LEADERBOARD.filter((r) => state.filter === "all" || r.type === state.filter);
      const val = (r) => (state.key === "params" ? size(r.params) : r[state.key]);
      rows = rows.slice().sort((a, b) => {
        const x = val(a), y = val(b);
        if (typeof x === "string") return state.dir === "asc" ? x.localeCompare(y) : y.localeCompare(x);
        if (Number.isNaN(x)) return 1;
        if (Number.isNaN(y)) return -1;
        return state.dir === "asc" ? x - y : y - x;
      });
      const best = {};
      for (const k of ["text", "teds", "formula", "order", "overall"]) best[k] = Math[lowerBetter[k] ? "min" : "max"](...rows.map((r) => r[k]));
      const medals = state.key === "overall" && state.dir === "desc";
      body.innerHTML = rows.map((r, i) => `
        <tr class="${r.ours ? "ours" : ""}">
          <td class="rank">${medals && i < 3 ? `<span class="medal m${i + 1}">${i + 1}</span>` : i + 1}</td>
          <td class="name left">${esc(r.name)}${r.ours ? " (ours)" : ""}<small>${r.type === "General" ? "General VLM" : "Expert VLM"}</small></td>
          <td>${esc(r.params)}</td>
          <td class="${r.text === best.text ? "best" : ""}">${r.text.toFixed(3)}</td>
          <td class="${r.teds === best.teds ? "best" : ""}">${r.teds.toFixed(2)}</td>
          <td class="${r.formula === best.formula ? "best" : ""}">${r.formula.toFixed(3)}</td>
          <td class="${r.order === best.order ? "best" : ""}">${r.order.toFixed(3)}</td>
          <td><span class="cellbar"><i><b style="width:${r.overall}%"></b></i><span>${r.overall.toFixed(2)}</span></span></td>
        </tr>`).join("");
      heads.forEach((h) => h.classList.toggle("sorted", h.dataset.key === state.key));
    }
    heads.forEach((h) => h.addEventListener("click", () => {
      const key = h.dataset.key;
      state.dir = state.key === key ? (state.dir === "asc" ? "desc" : "asc") : h.dataset.dir || "asc";
      state.key = key;
      render();
    }));
    $$("#board-filter button").forEach((b) => b.addEventListener("click", () => {
      $$("#board-filter button").forEach((x) => x.classList.toggle("active", x === b));
      state.filter = b.dataset.filter;
      render();
    }));
    render();
  }

  /* ------------------------------------------------------------------ charts */
  function scatter() {
    const host = $("#chart-scatter");
    if (!host) return;
    const W = 640, H = 400, m = { l: 54, r: 20, t: 16, b: 46 };
    const svg = chart(host, W, H, "Text accuracy against table TEDS for the systems of the leaderboard");
    const x0 = 72, x1 = 99, y0 = 48, y1 = 76;
    const X = (v) => m.l + ((v - x0) / (x1 - x0)) * (W - m.l - m.r), Y = (v) => H - m.b - ((v - y0) / (y1 - y0)) * (H - m.t - m.b);
    svg.appendChild(el("rect", { x: m.l, y: Y(73), width: W - m.l - m.r, height: Y(71) - Y(73), fill: "rgba(245, 158, 11, .14)" }));
    svg.appendChild(el("text", { x: m.l + 8, y: Y(73) - 6, fill: "#a16207", "font-weight": 600 }, "TEDS plateau, 71–73%")).setAttribute("style", "fill:#a16207");
    for (let v = 50; v <= 75; v += 5) {
      svg.appendChild(el("line", { class: "grid", x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }));
      svg.appendChild(el("text", { x: m.l - 10, y: Y(v) + 4, "text-anchor": "end" }, v));
    }
    for (let v = 75; v <= 95; v += 5) svg.appendChild(el("text", { x: X(v), y: H - m.b + 20, "text-anchor": "middle" }, v));
    svg.appendChild(el("line", { class: "axis", x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }));
    svg.appendChild(el("text", { x: (m.l + W - m.r) / 2, y: H - 6, "text-anchor": "middle", class: "lbl" }, "Text accuracy (%)"));
    svg.appendChild(el("text", { x: 14, y: (m.t + H - m.b) / 2, "text-anchor": "middle", class: "lbl", transform: `rotate(-90 14 ${(m.t + H - m.b) / 2})` }, "Table TEDS (%)"));
    const labelled = { "DocAtlas-Deepseek": [13, 4, "start"], "PaddleOCR-VL": [-10, -8, "end"], "MinerU2.5": [10, 18, "start"], "Qwen3-VL": [-10, 4, "end"], "Qwen2.5-VL": [10, 4, "start"], "DotsOCR": [10, 16, "start"], "GPT4o": [-10, 4, "end"], "Dolphin": [-10, 4, "end"] };
    LEADERBOARD.forEach((r) => {
      const cx = X(100 * (1 - r.text)), cy = Y(r.teds);
      const color = r.ours ? "#f59e0b" : r.type === "General" ? "#7c3aed" : "#2563eb";
      const dot = el("circle", { class: "dot", cx, cy, r: r.ours ? 8 : 6, fill: color, "fill-opacity": r.ours ? 1 : 0.82, stroke: "#fff", "stroke-width": 2 });
      dot.addEventListener("pointermove", (evt) => showTip(evt, `<b>${esc(r.name)}</b>Text edit ${r.text.toFixed(3)} · TEDS ${r.teds.toFixed(2)} · Overall ${r.overall.toFixed(2)}`, color));
      dot.addEventListener("pointerleave", hideTip);
      svg.appendChild(dot);
      if (labelled[r.name]) {
        const [dx, dy, anchor] = labelled[r.name];
        const t = el("text", { x: cx + dx, y: cy + dy, "text-anchor": anchor, class: r.ours ? "lbl" : "" }, r.ours ? "Ours" : r.name);
        if (r.ours) t.setAttribute("style", "fill:#b45309;font-size:13px");
        svg.appendChild(t);
      }
    });
    host.insertAdjacentHTML("afterbegin", `<div class="chart-legend"><span><i style="background:#f59e0b"></i>DocAtlas-Deepseek</span><span><i style="background:#2563eb"></i>Expert VLMs</span><span><i style="background:#7c3aed"></i>General VLMs</span></div>`);
  }

  function chartTypes() {
    const host = $("#chart-types");
    if (!host) return;
    const W = 640, H = 360, m = { l: 44, r: 12, t: 14, b: 44 };
    const svg = chart(host, W, H, "Mean score per chart type for five models");
    const colors = ["#2563eb", "#f59e0b", "#14b8a6"], names = ["Bar", "Line", "Pie"];
    const Y = (v) => H - m.b - (v / 0.8) * (H - m.t - m.b);
    for (let v = 0; v <= 0.8; v += 0.2) {
      svg.appendChild(el("line", { class: "grid", x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }));
      svg.appendChild(el("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end" }, v.toFixed(1)));
    }
    const band = (W - m.l - m.r) / CHART_TYPES.length, bw = Math.min(30, band / 4.4);
    CHART_TYPES.forEach((d, i) => {
      const cx = m.l + band * (i + 0.5);
      d.v.forEach((v, j) => {
        const x = cx + (j - 1) * (bw + 5) - bw / 2;
        const bar = el("rect", { x, y: Y(0), width: bw, height: 0, rx: 5, fill: colors[j] });
        bar.addEventListener("pointermove", (evt) => showTip(evt, `<b>${esc(d.name)}</b>${names[j]} charts: ${v.toFixed(3)}`, colors[j]));
        bar.addEventListener("pointerleave", hideTip);
        svg.appendChild(bar);
        const grow = () => { bar.setAttribute("y", Y(v)); bar.setAttribute("height", Y(0) - Y(v)); };
        if (reduceMotion) grow();
        else onVisible(host, () => { bar.style.transition = `all .9s cubic-bezier(.2,.7,.2,1) ${i * 60 + j * 40}ms`; grow(); });
        svg.appendChild(el("text", { x: x + bw / 2, y: Y(v) - 5, "text-anchor": "middle", style: "font-size:10.5px" }, v.toFixed(2)));
      });
      svg.appendChild(el("text", { x: cx, y: H - m.b + 20, "text-anchor": "middle", class: "lbl" }, d.name));
    });
    svg.appendChild(el("line", { class: "axis", x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0) }));
    host.insertAdjacentHTML("afterbegin", `<div class="chart-legend">${names.map((n, j) => `<span><i style="background:${colors[j]}"></i>${n} charts</span>`).join("")}</div>`);
  }

  function adapt() {
    const host = $("#chart-adapt"), seg = $("#adapt-models");
    if (!host) return;
    const W = 620, H = 460, m = { l: 44, r: 12, t: 34, b: 52 };
    const cIn = "#38bdf8", cOut = "#fbbf24";
    function draw(d) {
      const svg = chart(host, W, H, `In-domain and out-of-domain accuracy of ${d.model} under each training strategy`);
      const lo = 40, hi = 92;
      const Y = (v) => H - m.b - ((v - lo) / (hi - lo)) * (H - m.t - m.b);
      for (let v = 40; v <= 90; v += 10) {
        svg.appendChild(el("line", { class: "grid", x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }));
        svg.appendChild(el("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end" }, v));
      }
      const [, baseIn, baseOut] = d.rows[0];
      [[baseIn, cIn], [baseOut, cOut]].forEach(([v, c]) => svg.appendChild(el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: c, "stroke-dasharray": "4 5", "stroke-opacity": 0.55 })));
      const band = (W - m.l - m.r) / d.rows.length, bw = 44;
      d.rows.forEach(([name, vin, vout], i) => {
        const cx = m.l + band * (i + 0.5);
        [[vin, cIn, -1, baseIn, "In-domain"], [vout, cOut, 1, baseOut, "Out-of-domain"]].forEach(([v, c, side, base, label]) => {
          const x = cx + side * (bw / 2 + 3) - bw / 2;
          const bar = el("rect", { x, y: Y(v), width: bw, height: Y(lo) - Y(v), rx: 6, fill: c, "fill-opacity": name === "DPO" || i === 0 ? 1 : 0.78 });
          bar.addEventListener("pointermove", (evt) => showTip(evt, `<b>${esc(d.model)} · ${esc(name)}</b>${label}: ${v.toFixed(1)}${i ? ` (${v - base >= 0 ? "+" : "−"}${Math.abs(v - base).toFixed(1)})` : ""}`, c));
          bar.addEventListener("pointerleave", hideTip);
          svg.appendChild(bar);
          svg.appendChild(el("text", { x: x + bw / 2, y: Y(v) - 20, "text-anchor": "middle", class: "lbl" }, v.toFixed(1)));
          if (i) {
            const delta = v - base, good = delta >= 0;
            const t = el("text", { x: x + bw / 2, y: Y(v) - 6, "text-anchor": "middle", "font-weight": 700 }, `${good ? "+" : "−"}${Math.abs(delta).toFixed(1)}`);
            t.setAttribute("style", `fill:${good ? "#34d399" : "#fb7185"};font-size:11.5px`);
            svg.appendChild(t);
          }
        });
        const t = el("text", { x: cx, y: H - m.b + 22, "text-anchor": "middle", class: "lbl" }, name);
        if (name === "DPO") t.setAttribute("style", "fill:#fbbf24");
        svg.appendChild(t);
      });
      svg.appendChild(el("line", { class: "axis", x1: m.l, x2: W - m.r, y1: Y(lo), y2: Y(lo) }));
      host.insertAdjacentHTML("afterbegin", `<div class="chart-legend"><span><i style="background:${cIn}"></i>In-domain</span><span><i style="background:${cOut}"></i>Out-of-domain</span><span>dashed: baseline</span></div>`);
    }
    seg.innerHTML = ADAPT.map((d, i) => `<button class="${i ? "" : "active"}">${esc(d.model)}</button>`).join("");
    $$("button", seg).forEach((b, i) => b.addEventListener("click", () => {
      $$("button", seg).forEach((x) => x.classList.toggle("active", x === b));
      draw(ADAPT[i]);
    }));
    draw(ADAPT[0]);
  }

  function lora() {
    const host = $("#chart-lora");
    if (!host) return;
    const W = 560, H = 300, m = { l: 50, r: 18, t: 14, b: 46 };
    const svg = chart(host, W, H, "Gain on new languages against change on base languages for six training configurations");
    const x0 = -14, x1 = 3, y0 = 7.5, y1 = 14.5;
    const X = (v) => m.l + ((v - x0) / (x1 - x0)) * (W - m.l - m.r), Y = (v) => H - m.b - ((v - y0) / (y1 - y0)) * (H - m.t - m.b);
    svg.appendChild(el("rect", { x: X(0), y: m.t, width: W - m.r - X(0), height: H - m.t - m.b, fill: "rgba(52, 211, 153, .12)" }));
    svg.appendChild(el("line", { x1: X(0), x2: X(0), y1: m.t, y2: H - m.b, stroke: "rgba(52, 211, 153, .6)", "stroke-dasharray": "4 4" }));
    const tag = el("text", { x: X(0) + 6, y: m.t + 14 }, "no forgetting");
    tag.setAttribute("style", "fill:#34d399;font-weight:600");
    svg.appendChild(tag);
    for (let v = 8; v <= 14; v += 2) {
      svg.appendChild(el("line", { class: "grid", x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }));
      svg.appendChild(el("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end" }, `+${v}`));
    }
    for (let v = -12; v <= 2; v += 4) svg.appendChild(el("text", { x: X(v), y: H - m.b + 18, "text-anchor": "middle" }, v > 0 ? `+${v}` : v === 0 ? "0" : `−${Math.abs(v)}`));
    svg.appendChild(el("line", { class: "axis", x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }));
    svg.appendChild(el("text", { x: (m.l + W - m.r) / 2, y: H - 6, "text-anchor": "middle", class: "lbl" }, "Base languages, Δ TEDS"));
    svg.appendChild(el("text", { x: 13, y: (m.t + H - m.b) / 2, "text-anchor": "middle", class: "lbl", transform: `rotate(-90 13 ${(m.t + H - m.b) / 2})` }, "New languages, Δ TEDS"));
    const place = { "Full SFT": [11, 4, "start"], "All layers": [-11, 4, "end"], "MLP only": [-11, 4, "end"], "MLP gate + down": [0, -13, "middle"], "All QKV": [11, 5, "start"], "QKV only": [0, 23, "middle"] };
    LORA.forEach((d) => {
      const cx = X(d.base), cy = Y(d.gain), color = d.best ? "#fbbf24" : "#8fa0dd";
      const dot = el("circle", { class: "dot", cx, cy, r: d.best ? 8 : 6, fill: color, stroke: "#0b1020", "stroke-width": 2 });
      dot.addEventListener("pointermove", (evt) => showTip(evt, `<b>${esc(d.full)}</b>New languages ${d.gain > 0 ? "+" : ""}${d.gain.toFixed(1)} TEDS · base languages ${d.base > 0 ? "+" : "−"}${Math.abs(d.base).toFixed(1)} TEDS`, color));
      dot.addEventListener("pointerleave", hideTip);
      svg.appendChild(dot);
      const [dx, dy, anchor] = place[d.name];
      const t = el("text", { x: cx + dx, y: cy + dy, "text-anchor": anchor, class: d.best ? "lbl" : "", style: "font-size:13px" }, d.name);
      if (d.best) t.setAttribute("style", "fill:#fbbf24;font-size:13px");
      svg.appendChild(t);
    });
  }

  function signal() {
    const host = $("#chart-signal");
    if (!host) return;
    const W = 560, H = 190, m = { l: 168, r: 26, t: 26, b: 30 };
    const svg = chart(host, W, H, "In-domain and out-of-domain accuracy of DeepseekOCR for three positive signals");
    const lo = 74, hi = 85;
    const X = (v) => m.l + ((v - lo) / (hi - lo)) * (W - m.l - m.r);
    for (let v = 74; v <= 84; v += 2) {
      svg.appendChild(el("line", { class: "grid", x1: X(v), x2: X(v), y1: m.t - 6, y2: H - m.b }));
      svg.appendChild(el("text", { x: X(v), y: H - m.b + 18, "text-anchor": "middle" }, v));
    }
    const cIn = "#38bdf8", cOut = "#fbbf24", rowH = (H - m.t - m.b) / SIGNAL.length;
    SIGNAL.forEach((d, i) => {
      const y = m.t + rowH * (i + 0.5);
      const name = el("text", { x: m.l - 14, y: y + 4, "text-anchor": "end", class: "lbl" }, d.name);
      if (d.best) name.setAttribute("style", "fill:#fbbf24");
      svg.appendChild(name);
      svg.appendChild(el("line", { x1: X(d.outD), x2: X(d.inD), y1: y, y2: y, stroke: "rgba(255,255,255,.22)", "stroke-width": 3, "stroke-linecap": "round" }));
      [[d.outD, cOut, "Out-of-domain", SIGNAL[0].outD], [d.inD, cIn, "In-domain", SIGNAL[0].inD]].forEach(([v, c, label, base]) => {
        const dot = el("circle", { class: "dot", cx: X(v), cy: y, r: 7, fill: c, stroke: "#0b1020", "stroke-width": 2 });
        dot.addEventListener("pointermove", (evt) => showTip(evt, `<b>${esc(d.name)}</b>${label}: ${v.toFixed(1)}`, c));
        dot.addEventListener("pointerleave", hideTip);
        svg.appendChild(dot);
        const delta = v - base;
        const t = el("text", { x: X(v), y: y - 13, "text-anchor": "middle", "font-weight": 600 }, i ? `${v.toFixed(1)} (${delta >= 0 ? "+" : "−"}${Math.abs(delta).toFixed(1)})` : v.toFixed(1));
        if (i) t.setAttribute("style", `fill:${delta >= 0 ? "#34d399" : "#fb7185"}`);
        svg.appendChild(t);
      });
    });
    host.insertAdjacentHTML("afterbegin", `<div class="chart-legend"><span><i style="background:${cOut}"></i>Out-of-domain</span><span><i style="background:${cIn}"></i>In-domain</span></div>`);
  }

  /* ------------------------------------------------------------------ figures: click to enlarge */
  function lightbox() {
    const box = $("#lightbox");
    if (!box) return;
    const img = $("img", box);
    const close = () => { box.classList.remove("show"); setTimeout(() => (box.hidden = true), 200); };
    $$(".figure img").forEach((fig) => fig.addEventListener("click", () => {
      img.src = fig.currentSrc || fig.src;
      img.alt = fig.alt;
      box.hidden = false;
      requestAnimationFrame(() => box.classList.add("show"));
    }));
    box.addEventListener("click", close);
    addEventListener("keydown", (evt) => { if (evt.key === "Escape" && !box.hidden) close(); });
  }

  /* ------------------------------------------------------------------ code tabs, copy buttons */
  function code() {
    const tabs = $$(".codebox [data-code]");
    tabs.forEach((t) => t.addEventListener("click", () => {
      tabs.forEach((x) => x.classList.toggle("active", x === t));
      $$(".code-pane[id^='code-']").forEach((p) => p.classList.toggle("hidden", p.id !== `code-${t.dataset.code}`));
    }));
    const copy = async (button, text) => {
      try {
        await navigator.clipboard.writeText(text);
      } catch (err) {
        const area = document.createElement("textarea");
        area.value = text; document.body.appendChild(area); area.select(); document.execCommand("copy"); area.remove();
      }
      const label = $("span", button), old = label.textContent;
      button.classList.add("done"); label.textContent = "Copied";
      setTimeout(() => { button.classList.remove("done"); label.textContent = old; }, 1600);
    };
    const codeBtn = $("#copy-code"), bibBtn = $("#copy-bib");
    if (codeBtn) codeBtn.addEventListener("click", () => copy(codeBtn, $(".code-pane[id^='code-']:not(.hidden)").textContent.trim()));
    if (bibBtn) bibBtn.addEventListener("click", () => copy(bibBtn, $("#bibtex").textContent.trim()));
  }

  const init = () => [chrome, globe, funnel, matrix, explorer, leaderboard, scatter, chartTypes, adapt, lora, signal, lightbox, code].forEach((fn) => {
    try { fn(); } catch (err) { console.error(err); }
  });
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init) : init();
})();
