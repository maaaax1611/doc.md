'use strict';
/* Optional helpers for canvas figures. Load with "lib: fig" in a figure's header comment.
   Everything hangs off one global, Fig, so it cannot collide with a project's own libraries. */
window.Fig = (() => {
  const root = document.documentElement;
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const MONO = '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace';
  const DISPLAY = '"IBM Plex Sans Condensed", "Arial Narrow", system-ui, sans-serif';

  /* Value of a CSS custom property, e.g. token('--accent'). Read it inside draw() so a theme switch is picked up. */
  const token = name => getComputedStyle(root).getPropertyValue(name).trim();

  function rgba(color, alpha) {
    let c = color.replace('#', '');
    if (c.length === 3) c = c.split('').map(x => x + x).join('');
    const v = parseInt(c, 16);
    return `rgba(${v >> 16 & 255},${v >> 8 & 255},${v & 255},${alpha})`;
  }

  /* Size the canvas backing store to its CSS box (capped at 2x) and clear it. Returns { ctx, w, h } in CSS pixels. */
  function fit(canvas) {
    const r = canvas.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.max(1, r.width), h = Math.max(1, r.height), W = Math.round(w * dpr), H = Math.round(h * dpr);
    if (canvas.width !== W || canvas.height !== H) { canvas.width = W; canvas.height = H; }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx, w, h };
  }

  /* Redraw when the canvas is resized or the colour scheme changes. Returns the redraw function. */
  function onRedraw(canvas, draw) {
    let queued = false;
    const redraw = () => { if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; draw(); }); };
    new ResizeObserver(redraw).observe(canvas);
    new MutationObserver(redraw).observe(root, { attributes: true, attributeFilter: ['data-theme'] });
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redraw);
    redraw();
    return redraw;
  }

  /* Animation loop that only runs while the element is on screen and the tab is visible.
     step(dt, t) gets seconds since the last frame and seconds of running time.
     Returns { play, pause, toggle, running }. With prefers-reduced-motion it starts paused. */
  function loop(el, step, { autoplay = true } = {}) {
    let wanted = autoplay && !reduceMotion, visible = false, raf = 0, last = 0, t = 0;
    const tick = now => {
      raf = 0;
      if (!(wanted && visible) || document.hidden) return;
      const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
      last = now; t += dt;
      step(dt, t);
      raf = requestAnimationFrame(tick);
    };
    const kick = () => { if (!raf && wanted && visible && !document.hidden) { last = 0; raf = requestAnimationFrame(tick); } };
    new IntersectionObserver(es => { visible = es[es.length - 1].isIntersecting; kick(); }).observe(el);
    document.addEventListener('visibilitychange', kick);
    return {
      play() { wanted = true; kick(); },
      pause() { wanted = false; },
      toggle() { wanted = !wanted; kick(); return wanted; },
      get running() { return wanted; },
    };
  }

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const ease = t => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

  return { token, rgba, fit, onRedraw, loop, clamp, lerp, ease, reduceMotion, MONO, DISPLAY };
})();
