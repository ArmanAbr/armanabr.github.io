/* Progressive enhancement only — every page works with JS disabled. */
(function () {
  "use strict";

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
        setTimeout(function () {
          btn.textContent = "copy";
          btn.classList.remove("done");
        }, 1600);
      };

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () { done(true); },
                                                 function () { done(false); });
      } else {
        // http://localhost and file:// fall back to the legacy path.
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
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

    // Every element carrying searchable metadata is a filter candidate.
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
        active.forEach(function (tag) {
          if (item.tags.indexOf(tag) === -1) matchesTags = false;
        });
        var show = matchesText && matchesTags;
        item.el.hidden = !show;
        if (show) visible++;
      });

      // Hide alphabet groups whose entries were all filtered out.
      document.querySelectorAll(".tag-group").forEach(function (group) {
        var any = group.querySelector("li:not([hidden])");
        group.hidden = !any;
      });

      if (emptyMsg) emptyMsg.hidden = visible !== 0;
      if (reset) reset.hidden = !q && active.size === 0;
    }

    if (input) {
      input.addEventListener("input", apply);
      input.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") { input.value = ""; apply(); }
      });
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
})();
