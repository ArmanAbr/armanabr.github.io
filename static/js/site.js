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

  /* ---------- "On this page": highlight the section being read ---------- */

  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".doc-body .toc a[href^='#']"));
  if (tocLinks.length) {
    var byId = {};
    tocLinks.forEach(function (a) { byId[decodeURIComponent(a.getAttribute("href").slice(1))] = a; });
    var heads = Array.prototype.slice.call(document.querySelectorAll(".prose h2[id], .prose h3[id], .prose h4[id]"))
      .filter(function (h) { return byId[h.id]; });
    var activeLink = null, ticking = false;
    var mark = function () {
      ticking = false;
      // The section being read is the last heading scrolled past the header.
      var current = null;
      for (var i = 0; i < heads.length; i++) {
        if (heads[i].getBoundingClientRect().top < 120) current = heads[i]; else break;
      }
      var link = current ? byId[current.id] : null;
      if (link === activeLink) return;
      if (activeLink) activeLink.classList.remove("active");
      if (link) link.classList.add("active");
      activeLink = link;
    };
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(mark); }
    }, { passive: true });
    mark();
  }

  /* ---------- filter bars (listing pages + tags page) ---------- */

  // Text box + topic chips (all must match) + field chips (any value within a
  // field, every field must match). Listing pages mirror the state in the URL
  // (?filter=…&tag=a,b&os=windows) so a filtered view can be linked to.
  document.querySelectorAll(".filter-bar").forEach(function (bar) {
    var selector = bar.getAttribute("data-filter-target");
    if (!selector) return;
    var containers = Array.prototype.slice.call(document.querySelectorAll(selector));
    if (!containers.length) return;

    var input = bar.querySelector(".filter-input");
    var reset = bar.querySelector("[data-reset]");
    var tagChips = Array.prototype.slice.call(bar.querySelectorAll(".chip[data-tag]"));
    var facetChips = Array.prototype.slice.call(bar.querySelectorAll(".chip[data-facet]"));
    var emptyMsg = document.querySelector("[data-empty]");
    var syncUrl = bar.hasAttribute("data-sync-url");
    var activeTags = new Set();
    var activeFacets = {};

    var items = [];
    containers.forEach(function (container) {
      container.querySelectorAll("[data-title], [data-name]").forEach(function (el) {
        var facets = {};
        Array.prototype.forEach.call(el.attributes, function (a) {
          if (a.name.indexOf("data-f-") === 0) facets[a.name.slice(7)] = a.value;
        });
        items.push({
          el: el,
          text: (el.getAttribute("data-title") || el.getAttribute("data-name") || "") +
                " " + (el.getAttribute("data-tags") || ""),
          tags: (el.getAttribute("data-tags") || "").split(/\s+/).filter(Boolean),
          facets: facets
        });
      });
    });

    function writeUrl(q) {
      if (!syncUrl || !window.history || !history.replaceState) return;
      var params = new URLSearchParams();
      if (q) params.set("filter", q);
      if (activeTags.size) params.set("tag", Array.from(activeTags).join(","));
      Object.keys(activeFacets).forEach(function (k) {
        if (activeFacets[k].size) params.set(k, Array.from(activeFacets[k]).join(","));
      });
      var qs = params.toString();
      history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
    }

    // Does an item pass every filter, optionally ignoring one facet (so that
    // facet's own chips can be counted against the other filters)?
    function matches(item, q, skipFacet) {
      if (q && item.text.indexOf(q) === -1) return false;
      var ok = true;
      activeTags.forEach(function (tag) { if (item.tags.indexOf(tag) === -1) ok = false; });
      Object.keys(activeFacets).forEach(function (k) {
        if (k === skipFacet) return;
        if (activeFacets[k].size && !activeFacets[k].has(item.facets[k])) ok = false;
      });
      return ok;
    }

    // Show how many results each chip would leave, and grey out dead ends.
    function updateChips(q) {
      facetChips.forEach(function (chip) {
        var k = chip.getAttribute("data-facet"), v = chip.getAttribute("data-value");
        var n = items.filter(function (it) {
          return it.facets[k] === v && matches(it, q, k);
        }).length;
        setChipCount(chip, n);
      });
      tagChips.forEach(function (chip) {
        var tag = chip.getAttribute("data-tag");
        var n = items.filter(function (it) {
          return it.tags.indexOf(tag) !== -1 && matches(it, q);
        }).length;
        setChipCount(chip, n);
      });
    }

    function setChipCount(chip, n) {
      var badge = chip.querySelector(".pill-count");
      if (badge) badge.textContent = n;
      var dead = n === 0 && !chip.classList.contains("on");
      chip.classList.toggle("is-empty", dead);
      chip.disabled = dead;
    }

    function apply() {
      var q = (input ? input.value : "").trim().toLowerCase();
      var visible = 0;
      items.forEach(function (item) {
        var show = matches(item, q);
        item.el.hidden = !show;
        if (show) visible++;
      });
      updateChips(q);
      document.querySelectorAll(".tag-group").forEach(function (group) {
        group.hidden = !group.querySelector("li:not([hidden])");
      });
      var anyFacet = Object.keys(activeFacets).some(function (k) { return activeFacets[k].size; });
      if (emptyMsg) emptyMsg.hidden = visible !== 0;
      if (reset) reset.hidden = !q && activeTags.size === 0 && !anyFacet;
      writeUrl(q);
    }

    function setTag(chip, on) {
      var tag = chip.getAttribute("data-tag");
      if (on) activeTags.add(tag); else activeTags.delete(tag);
      chip.classList.toggle("on", on);
      chip.setAttribute("aria-pressed", on ? "true" : "false");
      // A chosen topic from the folded list stays visible.
      var more = chip.closest("details");
      if (on && more) more.open = true;
    }
    function setFacet(chip, on) {
      var k = chip.getAttribute("data-facet"), v = chip.getAttribute("data-value");
      activeFacets[k] = activeFacets[k] || new Set();
      if (on) activeFacets[k].add(v); else activeFacets[k].delete(v);
      chip.classList.toggle("on", on);
      chip.setAttribute("aria-pressed", on ? "true" : "false");
    }

    tagChips.forEach(function (chip) {
      chip.setAttribute("aria-pressed", "false");
      chip.addEventListener("click", function () {
        setTag(chip, !activeTags.has(chip.getAttribute("data-tag"))); apply();
      });
    });
    facetChips.forEach(function (chip) {
      chip.setAttribute("aria-pressed", "false");
      chip.addEventListener("click", function () {
        var k = chip.getAttribute("data-facet");
        setFacet(chip, !(activeFacets[k] && activeFacets[k].has(chip.getAttribute("data-value")))); apply();
      });
    });
    if (input) {
      input.addEventListener("input", apply);
      input.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { input.value = ""; apply(); } });
    }
    if (reset) {
      reset.addEventListener("click", function () {
        if (input) input.value = "";
        tagChips.forEach(function (c) { setTag(c, false); });
        facetChips.forEach(function (c) { setFacet(c, false); });
        apply();
      });
    }

    // Restore state from the URL (also how old /tags/easy/ links land here).
    if (syncUrl) {
      var params = new URLSearchParams(location.search);
      if (input && params.get("filter")) input.value = params.get("filter");
      (params.get("tag") || "").split(",").filter(Boolean).forEach(function (t) {
        tagChips.forEach(function (c) { if (c.getAttribute("data-tag") === t) setTag(c, true); });
      });
      facetChips.forEach(function (c) {
        var vals = (params.get(c.getAttribute("data-facet")) || "").split(",");
        if (vals.indexOf(c.getAttribute("data-value")) !== -1) setFacet(c, true);
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
    var cssHref = document.querySelector('link[href*="static/css/style.css"]');
    var base = cssHref ? cssHref.getAttribute("href").replace(/static\/css\/style\.css(\?.*)?$/, "") : "";

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
        var heads = (d.headings || []).join(" ").toLowerCase();
        var hay = (d.title + " " + (d.description || "") + " " + (d.tags || []).join(" ") + " " +
                   (d.facets || []).join(" ") + " " + heads + " " + (d.text || "")).toLowerCase();
        var score = 0;
        if (d.title.toLowerCase().indexOf(q) !== -1) score += 10;
        if ((d.tags || []).some(function (t) { return t.toLowerCase().indexOf(q) !== -1; })) score += 5;
        if (heads.indexOf(q) !== -1) score += 3;
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

    // /?q=term (the search box Google can show for the site) opens search.
    var initialQ = new URLSearchParams(location.search).get("q");
    if (initialQ) { open(); input.value = initialQ; run(initialQ); }

    document.addEventListener("keydown", function (ev) {
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
      if (ev.key === "/" && !typing && overlay.hidden) { ev.preventDefault(); open(); }
      else if (ev.key === "Escape" && !overlay.hidden) { close(); }
    });
  }
})();
