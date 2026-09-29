/* neuroedge studio — the page (docs/spec/studio.md). Every string from the agent or a
   trace is set with textContent, never as HTML. Slice S3. */
"use strict";
(function () {
  const boot = JSON.parse(document.getElementById("ne-boot").textContent);
  const root = document.getElementById("studio");
  const h1 = document.createElement("h1");
  h1.textContent = I18N.vi.title + " · " + boot.agent;
  root.appendChild(h1);
})();
