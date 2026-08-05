/**
 * landing.js — Mobile nav toggle + scroll-triggered reveals for the
 * InvenTrack landing page. No dependencies, no API calls.
 */

document.addEventListener("DOMContentLoaded", () => {

  // ── Mobile nav toggle ──
  const nav = document.getElementById("lp-nav");
  const toggle = document.getElementById("lp-menu-toggle");

  toggle?.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(isOpen));
  });

  // Close the mobile panel after tapping a link
  nav?.querySelectorAll(".lp-mobile-panel a").forEach(link => {
    link.addEventListener("click", () => {
      nav.classList.remove("open");
      toggle?.setAttribute("aria-expanded", "false");
    });
  });

  // ── Reveal the hero shelf bars + feature cards once on screen ──
  // Baseline CSS already shows everything at full value (safe if this
  // script never runs). Only opt into the hidden/animate-in state once
  // we know we can actually observe and reveal it.
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReducedMotion || typeof IntersectionObserver === "undefined") return;

  document.documentElement.classList.add("js-ready");

  const shelfRows = document.querySelectorAll(".lp-shelf-row");
  const featureCards = document.querySelectorAll(".lp-feature-card");

  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.25 });

  shelfRows.forEach((row, i) => {
    // Small stagger so the bars fill one after another rather than at once
    row.style.setProperty("--delay", `${i * 90}ms`);
    revealObserver.observe(row);
  });

  featureCards.forEach((card, i) => {
    card.style.transitionDelay = `${(i % 3) * 70}ms`;
    revealObserver.observe(card);
  });
});
