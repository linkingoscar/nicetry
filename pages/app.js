(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const progress = document.getElementById('scrollProgress');
  const nav = document.getElementById('topNav');
  const visual = document.getElementById('pathVisual');

  const updateScroll = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = max > 0 ? window.scrollY / max : 0;
    progress.style.width = `${Math.min(100, Math.max(0, ratio * 100))}%`;
    nav.classList.toggle('scrolled', window.scrollY > 24);
  };
  updateScroll();
  window.addEventListener('scroll', updateScroll, { passive: true });

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    }
  }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

  document.querySelectorAll('[data-reveal]').forEach((el, index) => {
    if (!reducedMotion) el.style.transitionDelay = `${Math.min(index % 4, 3) * 55}ms`;
    observer.observe(el);
  });

  if (visual && !reducedMotion && window.matchMedia('(pointer:fine)').matches) {
    visual.addEventListener('pointermove', (event) => {
      const rect = visual.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      visual.style.transform = `rotateX(${(-y * 3.2).toFixed(2)}deg) rotateY(${(x * 4).toFixed(2)}deg) translateY(-2px)`;
    });
    visual.addEventListener('pointerleave', () => {
      visual.style.transform = 'rotateX(0deg) rotateY(0deg) translateY(0)';
    });
  }
})();
