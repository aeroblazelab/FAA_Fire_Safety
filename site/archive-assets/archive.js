// first-visit notice: shown once per browser session
(function () {
  var KEY = "archiveNoticeSeen";
  try { if (sessionStorage.getItem(KEY)) return; } catch (e) {}
  function show() {
    var o = document.createElement("div");
    o.id = "archive-modal-overlay";
    o.innerHTML = '<div id="archive-modal" role="dialog" aria-modal="true" aria-labelledby="am-title">' +
      '<h2 id="am-title">&#9888;&#65039; Unofficial Historical Archive</h2>' +
      '<p>This is a preserved <strong>snapshot of the former FAA Fire Safety website</strong> ' +
      '(fire.tc.faa.gov) as captured through <strong>October&nbsp;2025</strong>, rebuilt from the ' +
      'Internet Archive after the original site went offline.</p>' +
      '<p><strong>Content is historical record only and is no longer being updated.</strong> ' +
      'This archive is not affiliated with or endorsed by the Federal Aviation Administration. ' +
      'For current regulations and guidance, use the FAA’s ' +
      '<a href="https://drs.faa.gov/" target="_blank" rel="noopener">Dynamic Regulatory System (DRS)</a>.</p>' +
      '<p style="font-size:13.5px;color:#555;">Built and hosted by ' +
      '<a href="https://www.aeroblazelab.com/" target="_blank" rel="noopener">Aeroblaze Laboratory</a> ' +
      'to keep these essential presentations, reports, and test resources accessible to the community ' +
      'while official channels are unavailable. <a href="/about-archive">About this archive &rarr;</a></p>' +
      '<button type="button" id="am-ok">I understand &mdash; view the archive</button></div>';
    document.body.appendChild(o);
    document.getElementById("am-ok").addEventListener("click", function () {
      try { sessionStorage.setItem(KEY, "1"); } catch (e) {}
      o.remove();
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", show);
  else show();
})();

// handbook: collapse historical content behind a reveal button.
// The chapter listing spans several layout containers, so instead of a wrapper
// div we hide every element that FOLLOWS the button (walking sibling chains up
// to <main>/<body>), which works regardless of nesting.
(function () {
  var btn = document.getElementById("handbook-reveal-btn");
  if (!btn) return;
  var stopAt = btn.closest("main") || document.body;
  var hidden = [];
  var node = btn;
  while (node && node !== stopAt) {
    for (var sib = node.nextElementSibling; sib; sib = sib.nextElementSibling) {
      if (sib.tagName === "SCRIPT" || sib.tagName === "FOOTER") continue;
      hidden.push(sib);
      sib.classList.add("hb-hidden");
    }
    node = node.parentElement;
  }
  btn.addEventListener("click", function () {
    hidden.forEach(function (el) { el.classList.remove("hb-hidden"); });
    btn.style.display = "none";
  });
})();
