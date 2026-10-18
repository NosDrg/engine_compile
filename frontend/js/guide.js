// frontend/js/guide.js — Hướng dẫn page interactions

document.addEventListener('DOMContentLoaded', () => {
  // ── Code example tabs ──────────────────────────────────────────
  const tabBtns  = document.querySelectorAll('#example-tabs .tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const pane = document.getElementById(`pane-${btn.dataset.tab}`);
      if (pane) pane.classList.add('active');
    });
  });

  // ── Copy button ────────────────────────────────────────────────
  document.getElementById('btn-copy-example')?.addEventListener('click', async () => {
    const activePane = document.querySelector('.tab-pane.active pre');
    if (!activePane) return;
    const code = activePane.innerText;
    try {
      await navigator.clipboard.writeText(code);
      const btn = document.getElementById('btn-copy-example');
      btn.textContent = '✅ Đã copy!';
      setTimeout(() => { btn.textContent = '📋 Copy'; }, 2000);
    } catch (_) {
      const btn = document.getElementById('btn-copy-example');
      btn.textContent = '❌ Thất bại';
      setTimeout(() => { btn.textContent = '📋 Copy'; }, 2000);
    }
  });

  // ── TOC active scroll tracking ─────────────────────────────────
  const sections = document.querySelectorAll('.guide-content section[id]');
  const tocLinks  = document.querySelectorAll('.toc-list a');

  if (sections.length && tocLinks.length) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          tocLinks.forEach(a => {
            a.classList.toggle('active', a.getAttribute('href') === `#${entry.target.id}`);
          });
        }
      });
    }, { rootMargin: '-20% 0px -70% 0px' });

    sections.forEach(s => observer.observe(s));
  }

  // ── TOC smooth scroll ──────────────────────────────────────────
  tocLinks.forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = document.querySelector(link.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
});
