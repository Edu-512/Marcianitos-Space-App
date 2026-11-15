/* Run in the main document, not a Streamlit component iframe. */
(() => {
  if (!window.isSecureContext || !("serviceWorker" in navigator)) return;
  const script = document.currentScript;
  const root = new URL("../", script.src);
  window.addEventListener("load", () => {
    navigator.serviceWorker.register(new URL("service-worker.js", root), {
      scope: root.pathname,
      updateViaCache: "none",
    }).catch((error) => {
      // Installation is progressive enhancement; the online app remains usable.
      console.warn("Field Shift offline support could not be registered:", error);
    });
  }, { once: true });
})();
