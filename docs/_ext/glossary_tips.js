/* Hover tips for links to glossary terms (docs/_ext/glossary_tips.py).
 *
 * The build appends a call with the tips, keyed by link target relative to
 * the site root. A link in the page's main content whose target has a tip
 * shows it on hover and on keyboard focus; Escape closes it.
 */
function glossaryTips(tips) {
  "use strict";
  const root = new URL(
    document.documentElement.dataset.content_root || "./",
    location.href,
  );
  const targets = new Map();
  for (const [target, html] of Object.entries(tips)) {
    targets.set(new URL(target, root).href, html);
  }
  const targetOf = (link) => {
    const url = new URL(link.href);
    url.search = "";
    return url.href;
  };

  const tip = document.createElement("div");
  tip.className = "glossary-tip";
  tip.id = "glossary-tip";
  tip.setAttribute("role", "tooltip");
  tip.hidden = true;
  document.body.appendChild(tip);
  let current = null;
  let timer = 0;

  function place(link) {
    const gap = 6;
    const margin = 8;
    const box = link.getBoundingClientRect();
    const width = tip.offsetWidth;
    const height = tip.offsetHeight;
    const right = document.documentElement.clientWidth - width - margin;
    const left = Math.max(margin, Math.min(box.left, right));
    let top = box.bottom + gap;
    if (top + height > window.innerHeight - margin && box.top - gap - height > margin) {
      top = box.top - gap - height;
    }
    tip.style.left = `${left + window.scrollX}px`;
    tip.style.top = `${top + window.scrollY}px`;
  }
  function show(link) {
    clearTimeout(timer);
    if (current === link) return;
    hide();
    current = link;
    tip.innerHTML = targets.get(targetOf(link));
    tip.style.left = "0px";
    tip.style.top = "0px";
    tip.hidden = false;
    link.setAttribute("aria-describedby", tip.id);
    place(link);
  }
  function hide() {
    clearTimeout(timer);
    if (current) current.removeAttribute("aria-describedby");
    current = null;
    tip.hidden = true;
  }
  function later(action) {
    clearTimeout(timer);
    timer = setTimeout(action, 150);
  }

  const main = document.querySelector('[role="main"]') || document.body;
  for (const link of main.querySelectorAll("a[href]")) {
    if (!targets.has(targetOf(link))) continue;
    link.addEventListener("mouseenter", () => later(() => show(link)));
    link.addEventListener("mouseleave", () => later(hide));
    link.addEventListener("focus", () => show(link));
    link.addEventListener("blur", hide);
  }
  // The pointer may move onto the tip, for example to select its text.
  tip.addEventListener("mouseenter", () => clearTimeout(timer));
  tip.addEventListener("mouseleave", () => later(hide));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hide();
  });
}
