// Start page: builds the topic sections, the search and the list of embeddable figures from manifest.json.
(async () => {
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const cats = document.getElementById('cats');
  let m;
  try { m = await (await fetch('manifest.json', { cache: 'no-cache' })).json(); }
  catch (e) { cats.innerHTML = '<p class="empty">manifest.json could not be loaded. Serve the site through a web server.</p>'; return; }
  const L = m.labels || {};

  // Topic sections
  const isPlanned = p => p.status === 'planned' || p.status === 'geplant';
  const card = p => {
    const planned = isPlanned(p);
    const tags = (p.tags || []).map(t => `<span>${esc(t)}</span>`).join('');
    return `<a class="card${planned ? ' planned' : ''}" href="${planned ? '#' : esc(p.path)}" data-q="${esc([p.title, p.desc, ...(p.tags || [])].join(' ').toLowerCase())}"${planned ? ' aria-disabled="true" tabindex="-1"' : ''}>
      <span class="eyebrow">${esc(planned ? L.planned : L.page)}</span><h2>${esc(p.title)}</h2><p>${esc(p.desc)}</p><div class="tags">${tags}</div></a>`;
  };
  cats.innerHTML = m.categories.map(c => {
    const pages = m.pages.filter(p => p.category === c.id);
    // Optional sub-groups inside a category (c.groups = [{id, title}], page with p.group)
    const body = c.groups
      ? c.groups.map(g => { const ps = pages.filter(p => p.group === g.id); return ps.length ? `<h3 class="grp">${esc(g.title)}</h3><div class="cards">${ps.map(card).join('')}</div>` : ''; }).join('')
      : (pages.length ? `<div class="cards">${pages.map(card).join('')}</div>` : '');
    const head = c.title ? `<h2>${esc(c.title)}</h2>${c.desc ? `<p>${esc(c.desc)}</p>` : ''}` : '';
    return `<section class="cat" id="${esc(c.id || 'pages')}">${head}
      ${body || `<p class="empty">${esc(L.no_pages)}</p>`}</section>`;
  }).join('');

  // Search over title, description and tags
  const q = document.getElementById('q');
  q.addEventListener('input', () => {
    const terms = q.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    document.querySelectorAll('.cat').forEach(sec => {
      let any = false;
      sec.querySelectorAll('.card').forEach(c => { const hit = terms.every(t => c.dataset.q.includes(t)); c.hidden = !hit; any = any || hit; });
      sec.hidden = terms.length > 0 && !any;
    });
  });

  // Figures to embed
  const wlist = document.getElementById('wlist');
  if (wlist && m.widgets.length) {
    const base = new URL('widgets/', location.href).href;
    const snip = w => `<iframe src="${base}${w.slug}.html" width="100%" height="${w.height}" style="border:0"></iframe>`;
    document.getElementById('ex').textContent = snip(m.widgets.find(w => w.interactive) || m.widgets[0]);
    const groups = m.pages.filter(p => m.widgets.some(w => w.page === p.id));
    wlist.innerHTML = groups.map(p => `<h3>${esc(p.title)}</h3><div class="tbl"><table>
      <thead><tr><th>${esc(L.widget)}</th><th>${esc(L.embed)}</th><th></th></tr></thead><tbody>
      ${m.widgets.filter(w => w.page === p.id).map(w => `<tr><td><a href="widgets/${esc(w.slug)}.html">${esc(w.title)}</a><div class="meta">${esc(w.interactive ? L.interactive : L.sketch)} · ${esc(L.height)} ${w.height} px</div></td>
        <td class="snip"><code>${esc(snip(w))}</code></td><td><button class="btn copy" type="button">${esc(L.copy)}</button></td></tr>`).join('')}
      </tbody></table></div>`).join('');
    wlist.addEventListener('click', e => {
      const b = e.target.closest('button.copy'); if (!b) return;
      const c = b.closest('tr').querySelector('code');
      const ok = () => { b.textContent = L.copied; setTimeout(() => b.textContent = L.copy, 1500); };
      const sel = () => { const r = document.createRange(); r.selectNodeContents(c); const s = getSelection(); s.removeAllRanges(); s.addRange(r); };
      (navigator.clipboard ? navigator.clipboard.writeText(c.textContent).then(ok, sel) : sel());
    });
  } else if (wlist) {
    document.getElementById('widgets').hidden = true;
  }

  if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
})();
