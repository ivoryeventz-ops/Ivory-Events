/* Packages page as a tick list: no photos, no rates, no package numbers.
   Shown on a client link when that client's data.json has "packagesView": "list",
   and on the general page when its address ends in ?list. Otherwise this file does nothing.
   Everything is read from the Packages page itself, so the two never go out of step. */
(function () {
  if (window.parent === window) return;
  var root = document.documentElement, host;
  try { host = new URL(window.parent.location.href); } catch (e) { return; }
  var forced = /[?&]list\b/.test(host.search);
  root.style.visibility = 'hidden';   // so rates never flash up before we know which view this client gets
  var ready = new Promise(function (res) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', res); else res();
  });
  var client = fetch(new URL('data.json', host.href).href.split('?')[0] + '?t=' + Date.now(), { cache: 'no-store' })
    .then(function (r) { if (r.status === 404) return null; if (!r.ok) throw new Error('data'); return r.json(); });
  Promise.all([client.then(function (d) { return { d: d }; }, function () { return { failed: true }; }), ready]).then(function (a) {
    var c = a[0];
    if (forced || (c.d && c.d.packagesView === 'list')) build(c.d || {});
    else if (c.failed) document.body.innerHTML = '<p style="padding:2rem;text-align:center">This page could not load. Please check your connection and open the link again.</p>';
    root.style.visibility = '';
  }).catch(function () {
    document.body.innerHTML = '<p style="padding:2rem;text-align:center">This page could not load. Please open the link again.</p>';
    root.style.visibility = '';
  });

  var WA_NUM = '919846116300';
  var MONEY = /(?:\u20b9|\bRs\.?(?=\s*\d)|\bINR\b)/;
  function clean(t) {
    return String(t || '').replace(/\([^()]*(?:\u20b9|\bRs\b|\bINR\b)[^()]*\)/gi, '')
      .replace(/(?:[-\u2013\u2014:@]\s*)?(?:\u20b9|\bRs\.?|\bINR\b)\s*\d[\d,]*(?:\s*\/-)?(?:\s*\/\s*\w+)?/gi, '').replace(/\s+/g, ' ').trim();
  }
  function note(t) {   // a description that talks about price is left out altogether
    t = String(t || '').replace(/\s+/g, ' ').trim();
    return MONEY.test(t) || /\b(rates?|price[ds]?|charges?|cost|allowance|per extra)\b/i.test(t) ? '' : t;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text) n.textContent = text; return n; }
  function all(sel, from) { return Array.prototype.slice.call((from || document).querySelectorAll(sel)); }

  function read() {
    var groups = [];
    var inc = all('.inclusions-highlight li').map(function (li) { return { name: clean(li.textContent), sub: '' }; })
      .filter(function (x) { return x.name; });
    if (inc.length) groups.push({ title: 'Stage decoration', items: inc });
    var title = '', cur = null;
    all('main h2, main .item').forEach(function (n) {
      if (n.tagName === 'H2') { title = clean(n.textContent.replace(/^\s*\d+\s*\u00b7\s*/, '')); cur = null; return; }
      var input = n.querySelector('input[type="radio"], input[type="checkbox"]'), b = n.querySelector('label b');
      if (!input || !b || input.name === 'pkg') return;
      var name = clean(b.textContent);
      if (!name) return;
      var small = n.querySelector('label small');
      var sub = input.getAttribute('data-is-round-table') === 'true' ? 'Round tables with covers, centrepieces and Tiffany chairs' : note(small && small.textContent);
      if (!cur) { cur = { title: title || 'Additional services', items: [] }; groups.push(cur); }
      cur.items.push({ name: name, sub: sub, one: input.type === 'radio' ? input.name : '' });
    });
    if (/mandatory\s+generator|generator\s+mandatory/i.test(document.body.textContent)) groups.push({ title: 'Generator', items: [{ name: 'Generator', sub: 'Required for every event', fixed: true }] });
    return groups;
  }

  function build(d) {
    var groups = read(), main = document.querySelector('main');
    if (!main || !groups.length) throw new Error('layout');
    var css = el('style');
    css.textContent = '.lv .item{padding:.8rem 1rem}.lv .item label{display:grid;grid-template-columns:auto 1fr;column-gap:.75rem;align-items:start;cursor:pointer}' +
      '.lv .item input{position:static;margin:.2rem 0 0;width:1.15rem;height:1.15rem;grid-row:span 2;accent-color:#b08d57}.lv .item b,.lv .item small{grid-column:2;padding:0;margin:0}' +
      '.lv .item.selected{border-color:#b08d57;box-shadow:0 0 0 2px #b08d57}.lv h2 .num{margin-right:.2rem}' +
      '.ivory-stack-overlay{display:none!important}';
    document.head.appendChild(css);
    main.innerHTML = '';
    main.classList.add('lv');
    var left = el('div'), aside = el('aside');
    left.appendChild(el('div', 'intro-box', 'Tick the stage decoration items and services you would like, then send us your list on WhatsApp.'));
    var boxes = [];
    groups.forEach(function (g, gi) {
      var h = el('h2'); h.appendChild(el('span', 'num', (gi + 1) + ' \u00b7 ')); h.appendChild(document.createTextNode(g.title)); left.appendChild(h);
      var grid = el('div', 'grid');
      g.items.forEach(function (it) {
        var card = el('div', 'item'), lab = el('label'), cb = el('input');
        cb.type = 'checkbox';
        if (it.fixed) { cb.checked = true; cb.disabled = true; card.className += ' selected'; }
        lab.appendChild(cb); lab.appendChild(el('b', '', it.name));
        if (it.sub) lab.appendChild(el('small', '', it.sub));
        card.appendChild(lab); grid.appendChild(card);
        boxes.push({ cb: cb, card: card, g: g.title, name: it.name, one: it.one, fixed: it.fixed });
      });
      left.appendChild(grid);
    });
    aside.appendChild(el('h3', '', 'Your list'));
    var count = el('p', 'count'), lines = el('ul'); lines.id = 'lines';
    aside.appendChild(count); aside.appendChild(lines);
    var fields = {};
    [['nm', 'text', 'Your name', d.name], ['ph', 'tel', 'Phone or WhatsApp', ''], ['dt', 'date', 'Wedding date', d.wedding_date], ['vn', 'text', 'Church / hall and location', d.venue], ['msg', '', 'Anything else we should know?', '']].forEach(function (f) {
      var i = el(f[1] ? 'input' : 'textarea');
      if (f[1]) i.type = f[1]; else i.rows = 2;
      i.id = f[0]; i.placeholder = f[2]; i.setAttribute('aria-label', f[2]); i.value = f[3] || '';
      i.addEventListener('input', render); i.addEventListener('change', render);
      fields[f[0]] = i; aside.appendChild(i);
    });
    var go = el('a', 'btn', 'Send my list on WhatsApp'); go.id = 'go'; go.target = '_blank'; go.rel = 'noopener noreferrer';
    var clear = el('button', 'btn ghost', 'Clear all ticks'); clear.type = 'button';
    var warn = el('p', 'note warn'); warn.setAttribute('role', 'status');
    aside.appendChild(go); aside.appendChild(clear); aside.appendChild(warn);
    main.appendChild(left); main.appendChild(aside);

    function picked() { return boxes.filter(function (x) { return x.cb.checked && !x.fixed; }); }
    function render() {
      var sel = picked(), parts = [], last = '';
      lines.innerHTML = '';
      boxes.forEach(function (x) { x.card.classList.toggle('selected', x.cb.checked); });
      sel.forEach(function (x) {
        lines.appendChild(el('li', '', x.name));
        if (x.g !== last) { parts.push((parts.length ? '\n' : '') + x.g + ':'); last = x.g; }
        parts.push('\u2022 ' + x.name);
      });
      if (!sel.length) lines.appendChild(el('li', 'empty', 'Nothing selected yet'));
      count.textContent = sel.length + (sel.length === 1 ? ' item selected' : ' items selected');
      if (sel.length) warn.textContent = '';
      var v = function (k) { return fields[k].value.trim(); };
      var text = 'Hello Ivory Events, this is my list for the wedding.\n\nName: ' + (v('nm') || '-') + '\nPhone: ' + (v('ph') || '-') + '\nDate: ' + (v('dt') || '-') + '\nVenue: ' + (v('vn') || '-') + '\n\n' + parts.join('\n') + (v('msg') ? '\n\nNotes: ' + v('msg') : '');
      go.href = 'https://wa.me/' + WA_NUM + '?text=' + encodeURIComponent(text);
    }
    boxes.forEach(function (x) {
      x.cb.addEventListener('change', function () {   // where only one can be chosen (e.g. church decoration, cake), ticking one clears the other
        if (x.cb.checked && x.one) boxes.forEach(function (y) { if (y !== x && y.one === x.one) y.cb.checked = false; });
        render();
      });
    });
    go.addEventListener('click', function (e) { if (!picked().length) { e.preventDefault(); warn.textContent = 'Please tick at least one item first.'; } });
    clear.addEventListener('click', function () { boxes.forEach(function (x) { if (!x.fixed) x.cb.checked = false; }); render(); });
    render();
  }
})();
