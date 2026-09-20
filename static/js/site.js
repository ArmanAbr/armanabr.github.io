/* Progressive enhancement only - every page works with JS disabled. */
(function () {
  "use strict";

  var root = document.documentElement;

  /* ---------- theme toggle ---------- */

  var themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", next === "dark" ? "#0b0f14" : "#f6f8fb");
    });
  }

  /* ---------- mobile navigation ---------- */

  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (ev) {
      if (ev.target.closest("a")) {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---------- copy-to-clipboard on code blocks ---------- */

  document.querySelectorAll(".prose pre").forEach(function (pre) {
    var host = pre.closest(".codehilite") || pre;
    if (host.querySelector(".copy-btn")) return;

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.textContent = "copy";
    btn.setAttribute("aria-label", "Copy code to clipboard");

    btn.addEventListener("click", function () {
      var text = pre.innerText;
      var done = function (ok) {
        btn.textContent = ok ? "copied" : "failed";
        btn.classList.toggle("done", ok);
        setTimeout(function () { btn.textContent = "copy"; btn.classList.remove("done"); }, 1600);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      } else {
        var ta = document.createElement("textarea");
        ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select();
        var ok = false;
        try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
        document.body.removeChild(ta);
        done(ok);
      }
    });
    host.appendChild(btn);
  });

  /* ---------- filter bars (listing pages + tags page) ---------- */

  document.querySelectorAll(".filter-bar").forEach(function (bar) {
    var selector = bar.getAttribute("data-filter-target");
    if (!selector) return;
    var containers = Array.prototype.slice.call(document.querySelectorAll(selector));
    if (!containers.length) return;

    var input = bar.querySelector(".filter-input");
    var reset = bar.querySelector("[data-reset]");
    var chips = Array.prototype.slice.call(bar.querySelectorAll(".chip[data-tag]"));
    var emptyMsg = document.querySelector("[data-empty]");
    var active = new Set();

    var items = [];
    containers.forEach(function (container) {
      container.querySelectorAll("[data-title], [data-name]").forEach(function (el) {
        items.push({
          el: el,
          text: (el.getAttribute("data-title") || el.getAttribute("data-name") || "") +
                " " + (el.getAttribute("data-tags") || ""),
          tags: (el.getAttribute("data-tags") || "").split(/\s+/).filter(Boolean)
        });
      });
    });

    function apply() {
      var q = (input ? input.value : "").trim().toLowerCase();
      var visible = 0;
      items.forEach(function (item) {
        var matchesText = !q || item.text.indexOf(q) !== -1;
        var matchesTags = true;
        active.forEach(function (tag) { if (item.tags.indexOf(tag) === -1) matchesTags = false; });
        var show = matchesText && matchesTags;
        item.el.hidden = !show;
        if (show) visible++;
      });
      document.querySelectorAll(".tag-group").forEach(function (group) {
        group.hidden = !group.querySelector("li:not([hidden])");
      });
      if (emptyMsg) emptyMsg.hidden = visible !== 0;
      if (reset) reset.hidden = !q && active.size === 0;
    }

    if (input) {
      input.addEventListener("input", apply);
      input.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { input.value = ""; apply(); } });
    }
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        var tag = chip.getAttribute("data-tag");
        if (active.has(tag)) { active.delete(tag); chip.classList.remove("on"); }
        else { active.add(tag); chip.classList.add("on"); }
        apply();
      });
    });
    if (reset) {
      reset.addEventListener("click", function () {
        if (input) input.value = "";
        active.clear();
        chips.forEach(function (c) { c.classList.remove("on"); });
        apply();
      });
    }
    apply();
  });

  /* ---------- site search overlay ---------- */

  var overlay = document.getElementById("search-overlay");
  var openBtn = document.getElementById("search-open");
  var closeBtn = document.getElementById("search-close");
  var input = document.getElementById("search-input");
  var resultsEl = document.getElementById("search-results");
  var hintEl = document.getElementById("search-hint");

  if (overlay && openBtn && input && resultsEl) {
    var index = null;
    var loading = false;
    var activeIdx = -1;
    var current = [];

    // Resolve the index.json path relative to site root (../ depth from <link>).
    var cssHref = document.querySelector('link[href$="style.css"]');
    var base = cssHref ? cssHref.getAttribute("href").replace(/static\/css\/style\.css$/, "") : "";

    function loadIndex() {
      if (index || loading) return;
      loading = true;
      fetch(base + "index.json")
        .then(function (r) { return r.json(); })
        .then(function (data) { index = data; loading = false; if (input.value) run(input.value); })
        .catch(function () { loading = false; if (hintEl) hintEl.textContent = "Search index could not be loaded."; });
    }

    function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }

    function highlight(text, q) {
      var i = text.toLowerCase().indexOf(q);
      if (i === -1) return esc(text);
      return esc(text.slice(0, i)) + "<mark>" + esc(text.slice(i, i + q.length)) + "</mark>" + esc(text.slice(i + q.length));
    }

    function run(query) {
      var q = query.trim().toLowerCase();
      current = [];
      activeIdx = -1;
      if (!q) { resultsEl.innerHTML = ""; if (hintEl) { hintEl.hidden = false; hintEl.textContent = "Type to search across every writeup, post and cheatsheet."; } return; }
      if (!index) { loadIndex(); return; }

      var scored = [];
      index.forEach(function (d) {
        var hay = (d.title + " " + (d.description || "") + " " + (d.tags || []).join(" ") + " " + (d.text || "")).toLowerCase();
        var score = 0;
        if (d.title.toLowerCase().indexOf(q) !== -1) score += 10;
        if ((d.tags || []).some(function (t) { return t.toLowerCase().indexOf(q) !== -1; })) score += 5;
        if (hay.indexOf(q) !== -1) score += 1;
        if (score > 0) scored.push({ d: d, score: score });
      });
      scored.sort(function (a, b) { return b.score - a.score || (b.d.date || "").localeCompare(a.d.date || ""); });
      current = scored.slice(0, 12).map(function (s) { return s.d; });

      if (!current.length) {
        resultsEl.innerHTML = "";
        if (hintEl) { hintEl.hidden = false; hintEl.textContent = 'No results for "' + query + '".'; }
        return;
      }
      if (hintEl) hintEl.hidden = true;
      resultsEl.innerHTML = current.map(function (d, i) {
        var kind = (d.kind || "").replace(/^\w/, function (c) { return c.toUpperCase(); });
        var meta = [kind, d.date, (d.tags || []).slice(0, 3).map(function (t) { return "#" + t; }).join(" ")].filter(Boolean).join("  ·  ");
        return '<li class="search-result' + (i === 0 ? " active" : "") + '"><a href="' + base + d.url + '">' +
               '<span class="search-result-title">' + highlight(d.title, q) + "</span>" +
               '<span class="search-result-meta"><span class="search-result-kind">' + esc(kind) + "</span>" +
               "<span>" + esc(d.date || "") + "</span><span>" + esc((d.tags || []).slice(0, 3).map(function (t) { return "#" + t; }).join(" ")) + "</span></span></a></li>";
      }).join("");
      activeIdx = 0;
    }

    function setActive(i) {
      var nodes = resultsEl.querySelectorAll(".search-result");
      if (!nodes.length) return;
      activeIdx = (i + nodes.length) % nodes.length;
      nodes.forEach(function (n, idx) { n.classList.toggle("active", idx === activeIdx); });
      nodes[activeIdx].scrollIntoView({ block: "nearest" });
    }

    function open() {
      overlay.hidden = false;
      loadIndex();
      setTimeout(function () { input.focus(); input.select(); }, 20);
    }
    function close() { overlay.hidden = true; }

    openBtn.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);
    overlay.addEventListener("mousedown", function (ev) { if (ev.target === overlay) close(); });
    input.addEventListener("input", function () { run(input.value); });
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowDown") { ev.preventDefault(); setActive(activeIdx + 1); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); setActive(activeIdx - 1); }
      else if (ev.key === "Enter") {
        var nodes = resultsEl.querySelectorAll(".search-result a");
        if (nodes[activeIdx]) window.location.href = nodes[activeIdx].getAttribute("href");
      }
    });

    document.addEventListener("keydown", function (ev) {
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
      if (ev.key === "/" && !typing && overlay.hidden) { ev.preventDefault(); open(); }
      else if (ev.key === "Escape" && !overlay.hidden) { close(); }
    });
  }
})();
