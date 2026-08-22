/* InkGuard — Website Scripts */

"use strict";

// ── Mobile nav toggle ────────────────────────────────────────
const hamburger  = document.getElementById("hamburger");
const mobileMenu = document.getElementById("mobileMenu");

if (hamburger && mobileMenu) {
  hamburger.addEventListener("click", () => {
    const isOpen = mobileMenu.classList.toggle("open");
    hamburger.setAttribute("aria-expanded", isOpen);
    mobileMenu.setAttribute("aria-hidden", !isOpen);
    // Animate hamburger → X
    const spans = hamburger.querySelectorAll("span");
    if (isOpen) {
      spans[0].style.transform = "translateY(7px) rotate(45deg)";
      spans[1].style.opacity   = "0";
      spans[2].style.transform = "translateY(-7px) rotate(-45deg)";
    } else {
      spans[0].style.transform = "";
      spans[1].style.opacity   = "";
      spans[2].style.transform = "";
    }
  });

  // Close on link click
  mobileMenu.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => {
      mobileMenu.classList.remove("open");
      hamburger.setAttribute("aria-expanded", "false");
      mobileMenu.setAttribute("aria-hidden", "true");
      const spans = hamburger.querySelectorAll("span");
      spans[0].style.transform = "";
      spans[1].style.opacity   = "";
      spans[2].style.transform = "";
    });
  });
}

// ── Nav shrink on scroll ─────────────────────────────────────
const nav = document.getElementById("nav");
let lastScroll = 0;

window.addEventListener("scroll", () => {
  const current = window.scrollY;
  if (current > 60) {
    nav.style.borderBottomColor = "rgba(30,41,59,0.8)";
  } else {
    nav.style.borderBottomColor = "";
  }
  lastScroll = current;
}, { passive: true });

// ── Scroll reveal ────────────────────────────────────────────
const revealElements = document.querySelectorAll("[data-reveal], .step, .feat-card");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        // Stagger cards in a grid
        const siblings = Array.from(entry.target.parentElement.children);
        const idx = siblings.indexOf(entry.target);
        const delay = entry.target.classList.contains("feat-card") ? idx * 60 : 0;
        setTimeout(() => {
          entry.target.classList.add("visible");
        }, delay);
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
);

revealElements.forEach(el => observer.observe(el));

// ── Copy workflow code ────────────────────────────────────────
const copyBtn      = document.getElementById("copyBtn");
const workflowCode = document.getElementById("workflowCode");

if (copyBtn && workflowCode) {
  copyBtn.addEventListener("click", async () => {
    const text = workflowCode.textContent;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied!";
      copyBtn.style.color  = "#22d3ee";
      copyBtn.style.borderColor = "#22d3ee";
      setTimeout(() => {
        copyBtn.textContent = "Copy";
        copyBtn.style.color  = "";
        copyBtn.style.borderColor = "";
      }, 2000);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity  = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      copyBtn.textContent = "Copied!";
      setTimeout(() => { copyBtn.textContent = "Copy"; }, 2000);
    }
  });
}

// ── Smooth anchor scroll (offset for sticky nav) ─────────────
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener("click", (e) => {
    const target = document.querySelector(anchor.getAttribute("href"));
    if (!target) return;
    e.preventDefault();
    const navH = nav ? nav.offsetHeight : 60;
    const top  = target.getBoundingClientRect().top + window.scrollY - navH - 12;
    window.scrollTo({ top, behavior: "smooth" });
  });
});

// ── Animate bar fills on load ─────────────────────────────────
window.addEventListener("load", () => {
  document.querySelectorAll(".bar-fill").forEach(bar => {
    const target = bar.style.width;
    bar.style.width = "0";
    setTimeout(() => { bar.style.width = target; }, 600);
  });
});