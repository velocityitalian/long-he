(() => {
  'use strict';

  const D = window.__THUMB__;
  if (!D) { console.warn('thumb.js: no data injected'); return; }

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pad2 = (n) => String(n).padStart(2, '0');
  const hexToRgb = (hex) => {
    const h = hex.replace('#', '');
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  };
  const shade = (hex, amount) => {
    const [r, g, b] = hexToRgb(hex).map((c) => Math.max(0, Math.min(255, Math.round(c * (1 + amount)))));
    return `rgb(${r}, ${g}, ${b})`;
  };
  const alpha = (hex, a) => {
    const [r, g, b] = hexToRgb(hex);
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  };

  const brandBlock = (light) => `
    <div class="brand ${light ? 'light' : ''}">
      <span class="mark">${makeIcon('bolt')}</span>
      <span class="btext"><b>${esc(D.brandTop)}</b><i>${esc(D.brandBottom)}</i></span>
    </div>`;

  const chapterPill = (h, light) => `
    <div class="pill-chapter ${light ? 'light' : ''}">
      <span class="pico">${makeIcon(h.icon)}</span>CHAPTER ${pad2(h.num)} · ${esc(h.chapter.toUpperCase())}
    </div>`;

  const eyebrow = () => `
    <div class="eyebrow"><img class="flag" src="flags/${esc(D.flag)}.png" alt=""> LEARN ${esc(D.language.toUpperCase())}</div>`;

  const statBadge = () => `${D.lesson.phrases} PHRASES · ${D.lesson.minutes} MIN`;

  const sayBlock = (h) => (h.transliteration ? `
    <div class="say" data-fit="say"><span>${esc(D.translitLabel)}</span><b>${esc(h.transliteration)}</b></div>` : '');

  const copyBlock = (h) => `
    <div class="copy">
      ${eyebrow()}
      <div class="nat" data-fit="nat">${esc(h.native)}</div>
      <div class="en" data-fit="en">${esc(h.english)}</div>
      ${sayBlock(h)}
      <div class="badges">
        <span class="badge new">NEW LESSON</span>
        <span class="badge">${statBadge()}</span>
      </div>
    </div>`;

  const panelBlock = (h) => `
    <div class="panel">
      <div class="pchapter">CHAPTER ${pad2(h.num)} OF ${pad2(D.lesson.chapters)}</div>
      <div class="pnative">${esc(h.chapterNative || h.chapter)}</div>
      <div class="picon">${makeIcon(h.icon)}</div>
      <div class="pnum">${pad2(h.num)}</div>
    </div>`;

  const sprinkle = (items) => items.map(([x, y, c, rot, round]) =>
    `<i class="sp ${round ? 'round' : ''}" style="left:${x}px;top:${y}px;background:${c};transform:rotate(${rot || 0}deg)"></i>`).join('');

  const MARK = '#FFD84D';
  const GREEN = '#58CC02';
  const CORAL = '#FF5B5B';
  const BLUE = '#1CB0F6';

  const templates = [
    // 1 · cream hero
    (h) => `
      <div class="bg cream"></div>
      <div class="blob" style="left:760px;top:-150px;width:660px;height:660px;background:${alpha(h.accent, .16)}"></div>
      <div class="blob" style="left:1040px;top:400px;width:420px;height:420px;background:${alpha(h.accent, .11)}"></div>
      <div class="grid-dots"></div>
      ${sprinkle([[905, 170, MARK, 20], [1180, 300, CORAL, -15, true], [830, 560, GREEN, 10], [1216, 560, BLUE, 30, true], [770, 430, h.accent, -20]])}
      ${brandBlock(false)}
      ${chapterPill(h, false)}
      ${copyBlock(h)}
      <div class="art-disc"></div>
      <div class="art-ring"></div>
      <div class="icon-sticker">${makeIcon(h.icon)}</div>
      <div class="bird">${MASCOT_SVG}</div>`,

    // 2 · white card on accent
    (h) => `
      <div class="bg accent"></div>
      <div class="blob" style="right:-160px;top:-180px;width:720px;height:720px;border:54px solid rgba(255,255,255,.08)"></div>
      <div class="blob" style="left:-120px;bottom:-220px;width:520px;height:520px;background:rgba(255,255,255,.07)"></div>
      <div class="card"></div>
      ${brandBlock(false)}
      ${chapterPill(h, false)}
      ${copyBlock(h)}
      <div class="art-disc"></div>
      ${sprinkle([[210, 96, MARK, 18], [980, 620, CORAL, -12, true], [1160, 96, GREEN, 24]])}
      <div class="bird">${MASCOT_SVG}</div>
      <div class="spark-sticker">${makeIcon('sparkles')}</div>`,

    // 3 · accent split
    (h) => `
      <div class="bg cream"></div>
      <div class="blob" style="right:-140px;top:-120px;width:620px;height:620px;background:${alpha(h.accent, .13)}"></div>
      <div class="grid-dots"></div>
      ${panelBlock(h)}
      ${sprinkle([[720, 120, h.accent, 18], [1190, 200, MARK, -14, true], [980, 610, GREEN, 22], [1230, 470, CORAL, 0, true]])}
      ${brandBlock(false)}
      ${chapterPill(h, false)}
      ${copyBlock(h)}
      <div class="bird">${MASCOT_SVG}</div>`,

    // 4 · full colour poster
    (h) => `
      <div class="bg accent"></div>
      <div class="blob" style="left:-140px;top:-160px;width:640px;height:640px;background:rgba(255,255,255,.07)"></div>
      <div class="pnum-bg">${pad2(h.num)}</div>
      ${sprinkle([[860, 180, MARK, 16], [1200, 300, BLUE, -10, true], [900, 640, CORAL, 0, true], [760, 96, GREEN, 28]])}
      ${brandBlock(true)}
      ${chapterPill(h, true)}
      ${copyBlock(h)}
      <div class="bird">${MASCOT_SVG}</div>`,

    // 5 · speech bubble
    (h) => `
      <div class="bg cream"></div>
      <div class="blob" style="left:-180px;top:300px;width:660px;height:660px;background:${alpha(h.accent, .17)}"></div>
      <div class="blob" style="right:-120px;top:-140px;width:500px;height:500px;background:${alpha(h.accent, .10)}"></div>
      <div class="grid-dots"></div>
      ${brandBlock(false)}
      ${chapterPill(h, false)}
      ${sprinkle([[360, 180, MARK, 20], [1220, 120, CORAL, -16, true], [1060, 640, GREEN, 12], [700, 92, BLUE, 0, true]])}
      <div class="bubble">
        ${eyebrow()}
        <div class="nat" data-fit="nat">${esc(h.native)}</div>
        <div class="en" data-fit="en">${esc(h.english)}</div>
        ${sayBlock(h)}
        <div class="badges">
          <span class="badge new">CAN YOU SAY IT?</span>
          <span class="badge">${statBadge()}</span>
        </div>
      </div>
      <div class="new-sticker">NEW!</div>
      <div class="bird">${MASCOT_SVG}</div>`,

    // 6 · night split
    (h) => `
      <div class="bg dark"></div>
      <div class="grid-dots"></div>
      ${panelBlock(h)}
      ${sprinkle([[760, 120, MARK, 18], [1210, 240, GREEN, -12, true], [1010, 620, BLUE, 24], [660, 600, CORAL, 0, true]])}
      ${brandBlock(true)}
      ${chapterPill(h, true)}
      ${copyBlock(h)}
      <div class="bird">${MASCOT_SVG}</div>`,
  ];

  function fitLine(el, maxH, min) {
    let size = parseFloat(getComputedStyle(el).fontSize);
    for (let i = 0; i < 90 && size > min; i++) {
      if (el.scrollHeight <= maxH && el.scrollWidth <= el.clientWidth + 1) break;
      size -= 2;
      el.style.fontSize = size + 'px';
    }
  }

  function fitSay(el) {
    const b = el.querySelector('b');
    if (!b) return;
    let size = parseFloat(getComputedStyle(b).fontSize);
    for (let i = 0; i < 60 && size > 15; i++) {
      if (el.offsetHeight <= 88) break;
      size -= 1;
      b.style.fontSize = size + 'px';
    }
  }

  function fitAll() {
    document.querySelectorAll('[data-fit="nat"]').forEach((el) => fitLine(el, 232, 42));
    document.querySelectorAll('[data-fit="en"]').forEach((el) => fitLine(el, 128, 26));
    document.querySelectorAll('[data-fit="say"]').forEach(fitSay);
  }

  window.renderThumb = (index) => {
    window.thumbReady = false;
    const i = ((index % templates.length) + templates.length) % templates.length;
    const h = D.heroes[i % D.heroes.length];
    const root = document.documentElement;
    root.style.setProperty('--accent', h.accent);
    root.style.setProperty('--accent-deep', shade(h.accent, -0.30));
    root.style.setProperty('--accent-soft', alpha(h.accent, 0.15));
    root.style.setProperty('--accent-line', alpha(h.accent, 0.30));

    const board = document.getElementById('board');
    board.className = 'thumb v' + (i + 1) + (D.rtl ? ' rtl' : '') + (D.hasScript ? ' script' : '');
    board.innerHTML = templates[i](h);

    const images = Array.from(board.querySelectorAll('img'));
    const loaded = Promise.all(images.map((img) => (
      img.complete ? Promise.resolve() : new Promise((resolve) => {
        img.onload = resolve;
        img.onerror = resolve;
      })
    )));

    Promise.all([document.fonts.ready, loaded]).then(() => {
      fitAll();
      window.thumbReady = true;
    });
  };
})();
