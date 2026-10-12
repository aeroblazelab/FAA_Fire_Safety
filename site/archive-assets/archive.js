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

// handbook: collapse historical content behind a reveal button
(function () {
  var hist = document.getElementById("handbook-historical");
  if (!hist) return;
  var btn = document.getElementById("handbook-reveal-btn");
  btn.addEventListener("click", function () {
    hist.style.display = "";
    btn.style.display = "none";
  });
})();
