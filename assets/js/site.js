/* ==========================================================================
   MINDSCAPE PROPERTIES — shared site script
   Loaded on every page. Every block is guarded, so a page that doesn't have
   a given element simply skips that feature.
   ========================================================================== */

/* ----------------------------------------------------------------
   CONTACT FORM DELIVERY  — pick ONE option:

   A) EASIEST — Web3Forms (free, no code): go to https://web3forms.com,
      register with  mindscapeproperties55@gmail.com , copy the access
      key it shows you, and paste it below. Enquiries then land in that
      Gmail inbox. No rebuild needed after pasting.
        const WEB3FORMS_KEY = "your-key-here";

   B) Any other form service (Formspree, etc.): paste its POST URL:
        const FORM_ENDPOINT = "https://formspree.io/f/xxxx";

   Until a key is set, the form opens the visitor's email app pre-filled
   to CONTACT_EMAIL (below).
------------------------------------------------------------------- */
const WEB3FORMS_KEY = "d2e735d7-83a7-45fb-af63-a17efd1eaa64"; // delivers enquiries to mindscapeproperties55@gmail.com
const FORM_ENDPOINT = ""; // alternative: a full POST endpoint URL
const CONTACT_EMAIL = "mindscapeproperties55@gmail.com";

(function () {
  "use strict";

  // Sticky nav — .solid keeps the bar filled on subpages (no full-bleed hero)
  const header = document.getElementById("header");
  if (header) {
    const forceSolid = header.classList.contains("solid");
    const onScroll = () => header.classList.toggle("scrolled", window.scrollY > 40);
    if (!forceSolid) { onScroll(); window.addEventListener("scroll", onScroll, { passive: true }); }
  }

  // Mobile menu
  const burger = document.getElementById("burger");
  const navLinks = document.getElementById("navLinks");
  if (burger && navLinks) {
    burger.addEventListener("click", () => navLinks.classList.toggle("open"));
    navLinks.querySelectorAll("a").forEach((a) =>
      a.addEventListener("click", () => navLinks.classList.remove("open"))
    );
  }

  // Hero background fade-in once the image is decoded
  const heroBg = document.querySelector(".hero-bg[data-img]");
  if (heroBg) {
    const src = heroBg.dataset.img;
    heroBg.style.backgroundImage = `url('${src}')`;
    const pre = new Image();
    pre.onload = () => (heroBg.style.opacity = "1");
    pre.src = src;
  }

  // Contact / enquiry form
  const form = document.getElementById("enquiryForm");
  if (form) {
    const statusEl = document.getElementById("formStatus");
    const property = form.dataset.property || "";
    const showStatus = (msg, ok) => {
      if (!statusEl) return;
      statusEl.textContent = msg;
      statusEl.className = "form-status show " + (ok ? "ok" : "err");
    };

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(form).entries());

      if (!data.name || !data.name.trim() || !data.email || !data.email.trim()) {
        showStatus("Please add your name and email so we can reply.", false);
        return;
      }
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(data.email)) {
        showStatus("That email doesn’t look right — mind checking it?", false);
        return;
      }

      const btn = form.querySelector("button[type=submit] span");
      const original = btn ? btn.textContent : "";
      const subject = property ? `Enquiry: ${property}` : `Property enquiry from ${data.name}`;

      const post = async (url, fd) => {
        if (btn) btn.textContent = "Sending…";
        try {
          const res = await fetch(url, { method: "POST", headers: { Accept: "application/json" }, body: fd });
          if (res.ok) {
            form.reset();
            showStatus("Thank you — your enquiry is in. We’ll be in touch within one business day.", true);
          } else {
            showStatus("Something went wrong. Please email us directly at " + CONTACT_EMAIL + ".", false);
          }
        } catch (err) {
          showStatus("Network issue. Please email us directly at " + CONTACT_EMAIL + ".", false);
        } finally {
          if (btn) btn.textContent = original;
        }
      };

      if (WEB3FORMS_KEY) {
        const fd = new FormData(form);
        fd.append("access_key", WEB3FORMS_KEY);
        fd.append("subject", subject);
        fd.append("from_name", "Mindscape Website");
        if (property) fd.append("property", property);
        await post("https://api.web3forms.com/submit", fd);
      } else if (FORM_ENDPOINT) {
        await post(FORM_ENDPOINT, new FormData(form));
      } else {
        const body =
          (property ? `Property: ${property}\n` : "") +
          `Name: ${data.name}\n` +
          `Email: ${data.email}\n` +
          `Phone: ${data.phone || "—"}\n` +
          `Interested in: ${data.intent || "—"}\n` +
          `Budget: ${data.budget || "—"}\n\n` +
          `Message:\n${data.message || "—"}`;
        window.location.href =
          `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        showStatus("Opening your email app to send this enquiry…", true);
      }
    });
  }

  // Gallery lightbox
  const galleryItems = Array.from(document.querySelectorAll(".gallery a"));
  const lb = document.getElementById("lightbox");
  if (lb && galleryItems.length) {
    const lbImg = document.getElementById("lbImg");
    let lbIndex = 0;
    const showLb = (i) => {
      lbIndex = (i + galleryItems.length) % galleryItems.length;
      lbImg.src = galleryItems[lbIndex].dataset.full;
    };
    const openLb = (i) => { showLb(i); lb.classList.add("open"); document.body.style.overflow = "hidden"; };
    const closeLb = () => { lb.classList.remove("open"); document.body.style.overflow = ""; };
    galleryItems.forEach((el, i) => el.addEventListener("click", () => openLb(i)));
    const q = (id) => document.getElementById(id);
    q("lbClose") && q("lbClose").addEventListener("click", closeLb);
    q("lbPrev") && q("lbPrev").addEventListener("click", (e) => { e.stopPropagation(); showLb(lbIndex - 1); });
    q("lbNext") && q("lbNext").addEventListener("click", (e) => { e.stopPropagation(); showLb(lbIndex + 1); });
    lb.addEventListener("click", (e) => { if (e.target === lb) closeLb(); });
    document.addEventListener("keydown", (e) => {
      if (!lb.classList.contains("open")) return;
      if (e.key === "Escape") closeLb();
      if (e.key === "ArrowLeft") showLb(lbIndex - 1);
      if (e.key === "ArrowRight") showLb(lbIndex + 1);
    });
  }

  // Scroll reveal
  const revealEls = document.querySelectorAll(".reveal:not(.in)");
  if (revealEls.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.14, rootMargin: "0px 0px -40px 0px" });
    revealEls.forEach((el) => io.observe(el));
  }
})();
