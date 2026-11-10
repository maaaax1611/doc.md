'use strict';
/* Bedienung aller Wiki-Seiten: Hell/Dunkel-Schalter, aktiver Eintrag im Inhaltsverzeichnis, Höhe von Widgets an die einbettende Seite melden. */
(() => {
const root = document.documentElement;
/* ---------- Darstellung umschalten ---------- */
(() => {
  const btns = [...document.querySelectorAll('.theme button')];
  if (!btns.length) return;
  let saved = 'system'; try { saved = localStorage.getItem('theme') || 'system'; } catch (e) {}
  function apply(t) {
    if (t === 'system') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', t);
    btns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.t === t)));
    try { localStorage.setItem('theme', t); } catch (e) {}
  }
  // kurzes Überblenden beim Umschalten, damit die Helligkeit nicht springt
  btns.forEach(b => b.addEventListener('click', () => { root.classList.add('theme-fade'); apply(b.dataset.t); setTimeout(() => root.classList.remove('theme-fade'), 260); }));
  if (!new URLSearchParams(location.search).get('theme')) apply(saved); else btns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.t === root.getAttribute('data-theme'))));
})();

/* ---------- Inhaltsverzeichnis ---------- */
(() => {
  const links = [...document.querySelectorAll('nav.toc a, .toc-mobile a')];
  const tm = document.querySelector('.toc-mobile'), cur = tm && tm.querySelector('.cur');
  const mark = id => { links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + id));
    if (cur) { const a = tm.querySelector(`a[href="#${CSS.escape(id)}"]`); cur.textContent = a ? [...a.children].map(x => x.textContent.trim()).join(' · ') : ''; } };
  const so = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) mark(e.target.id); }), { rootMargin: '-30% 0px -60% 0px' });
  document.querySelectorAll('main section[id]').forEach(s => so.observe(s));
  if (tm) {
    // Kopfbereich sichtbar: noch kein aktueller Abschnitt
    const head = document.querySelector('main > header');
    if (head) new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting && cur) { cur.textContent = ''; links.forEach(a => a.classList.remove('on')); } }), { rootMargin: '0px 0px -70% 0px' }).observe(head);
    // Schatten erst, wenn die Leiste klebt und Inhalt darunter durchläuft
    const s = document.createElement('div'); s.style.cssText = 'height:1px;margin-bottom:-1px'; tm.before(s);
    new IntersectionObserver(([e]) => tm.classList.toggle('stuck', !e.isIntersecting && e.boundingClientRect.top < 0)).observe(s);
    tm.addEventListener('click', e => { if (e.target.closest('a')) tm.open = false; });
  }
})();

/* ---------- Höhe an einbettende Seite melden (nur in Widgets) ---------- */
if (window.parent !== window) (() => {
  const send = () => { try { parent.postMessage({ xwiki: 'height', h: Math.ceil(document.documentElement.getBoundingClientRect().height) }, '*'); } catch (e) {} };
  new ResizeObserver(send).observe(document.body); addEventListener('load', send);
})();
})();
