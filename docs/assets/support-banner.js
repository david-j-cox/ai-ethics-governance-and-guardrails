(function () {
  var STORAGE_KEY = "rcai-support-banner-dismissed";
  var SHOW_AFTER_MS = 60000;

  if (localStorage.getItem(STORAGE_KEY) === "1") return;

  function build() {
    var banner = document.createElement("div");
    banner.className = "support-banner";
    banner.setAttribute("role", "complementary");
    banner.setAttribute("aria-label", "Support this project");
    banner.innerHTML =
      '<span class="support-banner__text">' +
      "This site is maintained by one person. If it's useful to you, " +
      '<a href="https://github.com/sponsors/david-j-cox" target="_blank" rel="noopener">sponsor on GitHub</a> ' +
      'or <a href="https://ko-fi.com/davidjcox" target="_blank" rel="noopener">tip on Ko-fi</a>.' +
      "</span>" +
      '<button type="button" class="support-banner__close" aria-label="Dismiss">Dismiss</button>';
    document.body.appendChild(banner);
    requestAnimationFrame(function () {
      banner.classList.add("is-visible");
    });
    banner.querySelector(".support-banner__close").addEventListener("click", function () {
      localStorage.setItem(STORAGE_KEY, "1");
      banner.classList.remove("is-visible");
      setTimeout(function () { banner.remove(); }, 300);
    });
  }

  setTimeout(build, SHOW_AFTER_MS);
})();
