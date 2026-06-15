(() => {
  const marker = document.querySelector("[data-auto-refresh='true']");
  if (marker) {
    window.setTimeout(() => window.location.reload(), 3000);
  }
})();
