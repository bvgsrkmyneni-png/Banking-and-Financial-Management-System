
(() => {
  const key = "fincore-theme";
  const button = document.getElementById("themeToggle");

  function applyTheme(theme) {
    document.body.dataset.theme = theme;

    if (button) {
      button.textContent =
        theme === "dark" ? "☀ Light Mode" : "☾ Dark Mode";
    }
  }

  let theme = "dark";

  try {
    theme = localStorage.getItem(key) === "light"
      ? "light"
      : "dark";
  } catch (error) {
    console.warn("Theme preference unavailable");
  }

  applyTheme(theme);

  button?.addEventListener("click", () => {
    theme = theme === "dark" ? "light" : "dark";
    applyTheme(theme);

    try {
      localStorage.setItem(key, theme);
    } catch (error) {
      console.warn("Could not save theme preference");
    }
  });
})();
