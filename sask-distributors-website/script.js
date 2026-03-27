const navToggle = document.querySelector(".nav-toggle");
const siteNav = document.querySelector(".site-nav");
const quoteForm = document.querySelector(".quote-form");
const statusEl = document.querySelector(".form-status");

if (navToggle && siteNav) {
  navToggle.addEventListener("click", () => {
    const open = siteNav.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(open));
  });
}

if (quoteForm && statusEl) {
  quoteForm.addEventListener("submit", (event) => {
    event.preventDefault();
    statusEl.textContent = "Thanks. Your request has been submitted.";
    quoteForm.reset();
  });
}
