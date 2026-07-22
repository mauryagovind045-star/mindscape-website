/* ==========================================================================
   MINDSCAPE PROPERTIES — listings filter + search
   Filters the server-rendered cards in place (kept in the HTML for SEO).
   Each .pcard carries: data-location, data-price, data-beds, data-text
   ========================================================================== */
(function () {
  "use strict";
  const grid = document.getElementById("listingsGrid");
  if (!grid) return;

  const cards = Array.from(grid.querySelectorAll(".pcard"));
  const fLoc = document.getElementById("f-location");
  const fPrice = document.getElementById("f-price");
  const fTerm = document.getElementById("f-term");   // rentals page: monthly / nightly
  const fBeds = document.getElementById("f-beds");
  const fSearch = document.getElementById("f-search");
  const reset = document.getElementById("f-reset");
  const countEl = document.getElementById("resultsCount");
  const noResults = document.getElementById("noResults");

  function apply() {
    const loc = (fLoc && fLoc.value) || "";
    const price = (fPrice && fPrice.value) || "";      // "min-max", max may be empty
    const term = (fTerm && fTerm.value) || "";
    const beds = parseInt((fBeds && fBeds.value) || "0", 10) || 0;
    const q = ((fSearch && fSearch.value) || "").trim().toLowerCase();

    let min = 0, max = Infinity;
    if (price) {
      const parts = price.split("-");
      min = parseInt(parts[0], 10) || 0;
      max = parts[1] ? parseInt(parts[1], 10) : Infinity;
    }

    let shown = 0;
    cards.forEach((card) => {
      const cLoc = card.dataset.location || "";
      const cPrice = parseInt(card.dataset.price || "0", 10) || 0;
      const cBeds = parseInt(card.dataset.beds || "0", 10) || 0;
      const cText = card.dataset.text || "";

      const ok =
        (!loc || cLoc === loc) &&
        (cPrice >= min && cPrice <= max) &&
        (!term || (card.dataset.term || "") === term) &&
        (!beds || cBeds >= beds) &&
        (!q || cText.indexOf(q) !== -1);

      card.style.display = ok ? "" : "none";
      if (ok) shown++;
    });

    if (countEl) countEl.innerHTML = "<b>" + shown + "</b> " + (shown === 1 ? "property" : "properties");
    if (noResults) noResults.classList.toggle("show", shown === 0);
  }

  [fLoc, fPrice, fTerm, fBeds].forEach((el) => el && el.addEventListener("change", apply));
  if (fSearch) fSearch.addEventListener("input", apply);
  if (reset) reset.addEventListener("click", () => {
    if (fLoc) fLoc.value = "";
    if (fPrice) fPrice.value = "";
    if (fTerm) fTerm.value = "";
    if (fBeds) fBeds.value = "";
    if (fSearch) fSearch.value = "";
    apply();
  });

  apply();
})();
