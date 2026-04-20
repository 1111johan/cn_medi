const apiBase = (import.meta.env.VITE_API_BASE || "").trim();
window.__TCM_API_BASE__ = apiBase;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const node = document.createElement("script");
    node.src = src;
    node.async = false;
    node.onload = () => resolve();
    node.onerror = () => reject(new Error(`load_failed:${src}`));
    document.body.appendChild(node);
  });
}

(async () => {
  await loadScript("/static/js/common.js");
  await loadScript("/static/js/smart_qa.js");
})();
