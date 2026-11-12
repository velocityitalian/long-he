(() => {
  'use strict';

  const T = window.__TIMELINE__;
  if (!T) { console.warn('scene.js: no timeline injected'); return; }

  const $ = (id) => document.getElementById(id);
  const clamp01 = (v) => Math.max(0, Math.min(1, v));
  const seg = (t, a, b) => clamp01((t - a) / Math.max(b - a, 1e-6));
  const easeOutCubic = (x) => 1 - Math.pow(1 - x, 3);
  const easeOutBack = (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtTime = (s) => { s = Math.max(0, s); const m = Math.floor(s / 60); return `${m}:${String(Math.floor(s % 60)).padStart(2, '0')}`; };
  const pad2 = (n) => String(n).padStart(2, '0');

  const tf = (el, x, y, s, r) => {
    el.style.transform = `translate(${x || 0}px, ${y || 0}px) scale(${s == null ? 1 : s}) rotate(${r || 0}deg)`;
  };
  const op = (el, o) => { el.style.opacity = String(o); };

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

  /* ------------------------------------------------------------- static setup */

  document.querySelectorAll('[data-icon]').forEach((el) => { el.innerHTML = makeIcon(el.dataset.icon); });
  document.querySelectorAll('.mascot').forEach((el) => { el.innerHTML = MASCOT_SVG; });

  $('brandTop').textContent = T.brand_top;
  $('brandBottom').textContent = T.brand_bottom;
  $('footBrand').textContent = T.brand;
  $('footHandle').textContent = T.handle;
  $('footLesson').textContent = `LESSON 01 · ${T.chapters.length} CHAPTERS`;
  $('natLabelText').textContent = T.language.native_label;
  $('translitLabel').textContent = T.language.translit_label;
  $('statChapters').textContent = T.chapters.length;
  $('statPhrases').textContent = T.phrases.length;
  $('statMinutes').textContent = T.minutes.toFixed(1);
  $('outroPhrases').textContent = T.phrases.length;
  $('outroChapters').textContent = T.chapters.length;
  $('outroMinutes').textContent = T.minutes.toFixed(1);
  $('outroSub').textContent = `${T.phrases.length} ${T.language.name} phrases across ${T.chapters.length} chapters`;
  $('ctaHandle').textContent = T.handle;

  const COPY = T.copy || {};
  if (COPY.intro_tag) $('introTag').innerHTML = COPY.intro_tag;
  if (COPY.intro_cta) $('introCta').innerHTML = `<span class="ico">${makeIcon('chevron')}</span>${esc(COPY.intro_cta)}`;
  if (COPY.outro_eyebrow) $('outroEyebrow').textContent = COPY.outro_eyebrow;
  if (COPY.outro_title) $('outroTitle').textContent = COPY.outro_title;

  const logoWord = $('logoWord');
  logoWord.innerHTML = T.brand_top.split('').map((c) => `<span>${c}</span>`).join('');
  const letters = Array.from(logoWord.querySelectorAll('span'));

  const rail = $('chapterRail');
  rail.innerHTML = T.chapters.map((ch, i) => `
    <div class="rail-item" data-i="${i}">
      <div class="rail-num">CHAPTER ${pad2(i + 1)}</div>
      <div class="rail-name">${esc(ch.english)}</div>
      <div class="rail-fill"></div>
    </div>`).join('');
  const railItems = Array.from(rail.children);

  $('introChips').innerHTML = T.chapters.map((ch) => `
    <div class="intro-chip">
      <span class="chip-ico" style="background:${ch.accent}">${makeIcon(ch.icon)}</span>
      ${esc(ch.english)}
    </div>`).join('');

  const samplePicks = [0, Math.floor(T.phrases.length / 2), T.phrases.length - 1].filter((v, i, a) => a.indexOf(v) === i);
  $('floatCards').innerHTML = samplePicks.map((idx, i) => {
    const p = T.phrases[idx];
    return `<div class="fcard fc${i + 1}" data-i="${i}">
      <div class="fcard-native">${esc(p.native)}</div>
      <div class="fcard-en">${esc(p.english)}</div>
      <div class="fcard-dot" style="background:${T.chapters[p.chapter].accent}"></div>
    </div>`;
  }).join('');
  const floatCards = Array.from(document.querySelectorAll('.fcard'));

  $('chapterSample').innerHTML = `
    <div class="note-chip">${makeIcon('speaker')}LISTEN</div>
    <div class="note-chip">${makeIcon('mic')}REPEAT</div>
    <div class="note-chip">${makeIcon('check')}REMEMBER</div>`;

  $('outroRecap').innerHTML = T.chapters.map((ch) => `
    <div class="recap-chip">
      <span class="chip-ico" style="background:${ch.accent}">${makeIcon(ch.icon)}</span>
      ${esc(ch.english)} <small>${ch.count} phrases</small>
    </div>`).join('');

  /* ------------------------------------------------------------- mascot anim */

  function blinkAt(t, phase) {
    const p = (t + phase) % 4.6;
    if (p < 0.18) return Math.max(0.08, 1 - Math.sin((p / 0.18) * Math.PI) * 0.94);
    return 1;
  }

  function animMascot(wrap, t, opts) {
    if (!wrap) return;
    const o = opts || {};
    const phase = o.phase || 0;
    const wave = o.wave || 0;
    const jump = o.jump || 0;
    const svg = wrap.querySelector('.velo');
    if (!svg) return;
    const bob = svg.querySelector('.velo-bob');
    if (bob) bob.setAttribute('transform', `translate(0 ${Math.sin(t * 2.2 + phase) * 7 - jump * 44})`);
    const tilt = svg.querySelector('.velo-tilt');
    if (tilt) tilt.setAttribute('transform', `rotate(${Math.sin(t * 1.4 + phase) * 2.2} 120 150)`);
    const blink = blinkAt(t, phase);
    for (const side of ['l', 'r']) {
      const eye = svg.querySelector('.velo-eye-' + side);
      if (!eye) continue;
      const cx = side === 'l' ? 86 : 154;
      eye.setAttribute('transform', `translate(${cx} 114) scale(1 ${blink})`);
    }
    const wl = 8 + Math.sin(t * 3.1 + phase) * 6 + wave * (26 + 22 * Math.sin(t * 13));
    const wr = 8 + Math.sin(t * 2.7 + phase + 1) * 6 + wave * (16 + 16 * Math.sin(t * 12 + 1));
    const wingL = svg.querySelector('.velo-wing-l');
    if (wingL) wingL.setAttribute('transform', `rotate(${-wl} 66 112)`);
    const wingR = svg.querySelector('.velo-wing-r');
    if (wingR) wingR.setAttribute('transform', `rotate(${wr} 174 112)`);
  }

  /* --------------------------------------------------------------- background */

  const blobs = ['.a1', '.a2', '.a3', '.a4'].map((s) => document.querySelector(s));
  function renderBg(t) {
    blobs[0].style.transform = `translate(${Math.sin(t * 0.16) * 52}px, ${Math.cos(t * 0.13) * 38}px)`;
    blobs[1].style.transform = `translate(${Math.cos(t * 0.15 + 2) * 46}px, ${Math.sin(t * 0.17) * 42}px)`;
    blobs[2].style.transform = `translate(${Math.sin(t * 0.14 + 1) * 44}px, ${Math.cos(t * 0.16) * 36}px)`;
    blobs[3].style.transform = `translate(${Math.cos(t * 0.12 + 3) * 40}px, ${Math.sin(t * 0.15) * 44}px)`;
    const wm = $('watermark');
    wm.style.transform = `rotate(-6deg) translate(${Math.sin(t * 0.1) * 26}px, ${Math.cos(t * 0.09) * 22}px)`;
    const gw = $('ghostWord');
    gw.style.transform = `rotate(-4deg) translate(${Math.sin(t * 0.23) * 18}px, ${Math.cos(t * 0.19) * 12}px)`;
  }

  const fx = $('fx');
  const fctx = fx.getContext('2d');
  const fxTop = $('fxTop');
  const tctx = fxTop.getContext('2d');

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function drawStar(ctx, cx, cy, r, points) {
    ctx.beginPath();
    for (let i = 0; i < points * 2; i++) {
      const a = -Math.PI / 2 + (i * Math.PI) / points;
      const rr = i % 2 ? r * 0.45 : r;
      const x = cx + Math.cos(a) * rr;
      const y = cy + Math.sin(a) * rr;
      if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    }
    ctx.closePath();
  }

  const glyphs = (T.language.glyphs || T.brand_top || 'VELOCITY').split('').filter(Boolean);
  const ambient = (() => {
    const rnd = mulberry32(2026);
    return Array.from({ length: 26 }, () => ({
      x: rnd() * 1920,
      y: rnd() * 1080,
      size: 34 + rnd() * 62,
      speed: 0.35 + rnd() * 0.7,
      amp: 20 + rnd() * 54,
      phase: rnd() * Math.PI * 2,
      glyph: glyphs[Math.floor(rnd() * glyphs.length)],
      rot: (rnd() - 0.5) * 24,
      tone: rnd(),
    }));
  })();

  function drawAmbient(t) {
    fctx.clearRect(0, 0, 1920, 1080);
    for (const s of ambient) {
      const y = (((s.y - t * s.speed * 22) % 1200) + 1200) % 1200 - 60;
      const x = s.x + Math.sin(t * 0.4 + s.phase) * s.amp;
      fctx.save();
      fctx.globalAlpha = 0.10;
      fctx.translate(x, y);
      fctx.rotate((s.rot + t * 4) * Math.PI / 180);
      fctx.font = `900 ${s.size}px Nunito, Script, Noto, sans-serif`;
      fctx.textAlign = 'center';
      fctx.fillStyle = s.tone > 0.55 ? '#30303A' : (s.tone > 0.28 ? '#58CC02' : '#1CB0F6');
      fctx.fillText(s.glyph, 0, 0);
      fctx.restore();
    }
  }

  const burstData = (T.fx || []).map((b, bi) => {
    const rnd = mulberry32(1000 + bi * 97);
    const n = Math.round((b.count || 34) * (b.power || 1));
    const parts = [];
    for (let i = 0; i < n; i++) {
      const ang = -Math.PI / 2 + (rnd() - 0.5) * 2.4;
      const spd = 380 + rnd() * 900;
      parts.push({
        vx: Math.cos(ang) * spd + (rnd() - 0.5) * 180,
        vy: Math.sin(ang) * spd,
        w: 9 + rnd() * 15,
        h: 7 + rnd() * 11,
        rot: rnd() * Math.PI * 2,
        vr: (rnd() - 0.5) * 14,
        life: 1.1 + rnd() * 1.2,
        color: ['#58CC02', '#1CB0F6', '#FFC800', '#FF4B4B', '#CE82FF', '#FF9600', '#FFFFFF', '#8FE63D'][Math.floor(rnd() * 8)],
        round: rnd() > 0.62,
        star: rnd() > 0.86,
      });
    }
    return { t: b.t, x: b.x, y: b.y, parts };
  });

  const GRAVITY = 1500;
  function drawTopFx(t) {
    tctx.clearRect(0, 0, 1920, 1080);
    for (const b of burstData) {
      const dt = t - b.t;
      if (dt < 0 || dt > 2.7) continue;
      for (const p of b.parts) {
        if (dt > p.life) continue;
        const x = b.x + p.vx * dt;
        const y = b.y + p.vy * dt + 0.5 * GRAVITY * dt * dt;
        if (y > 1160) continue;
        const a = 1 - clamp01((dt - p.life * 0.5) / (p.life * 0.5));
        tctx.save();
        tctx.globalAlpha = Math.max(0, a);
        tctx.translate(x, y);
        tctx.rotate(p.rot + p.vr * dt);
        tctx.fillStyle = p.color;
        if (p.star) { drawStar(tctx, 0, 0, p.w * 0.9, 5); tctx.fill(); }
        else if (p.round) { tctx.beginPath(); tctx.arc(0, 0, p.w * 0.42, 0, 7); tctx.fill(); }
        else { tctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); }
        tctx.restore();
      }
    }
  }

  /* -------------------------------------------------------------- phrases */

  let currentPhrase = -1;
  let currentChapter = -1;
  let enSpans = [];
  let viTiles = [];
  let enActive = -1;
  let viActive = -1;
  let stackHeights = { conn: 0, nat: 0, translit: 0, repeat: 0 };
  let bookSignature = null;

  const flowHeight = (el) => {
    if (!el || el.offsetHeight === 0) return 0;
    const cs = getComputedStyle(el);
    return el.offsetHeight + (parseFloat(cs.marginTop) || 0) + (parseFloat(cs.marginBottom) || 0);
  };

  function applyChapter(ch, index) {
    if (!ch) return;
    document.documentElement.style.setProperty('--accent', ch.accent);
    document.documentElement.style.setProperty('--accent-deep', shade(ch.accent, -0.28));
    document.documentElement.style.setProperty('--ambient', ch.ambient);

    $('watermark').textContent = pad2(index + 1);
    const sameName = ch.native.toLowerCase() === ch.english.toLowerCase();
    $('catText').textContent = sameName ? ch.english : `${ch.english} · ${ch.native}`;
    $('catIco').innerHTML = makeIcon(ch.icon);
    $('panelEyebrow').textContent = `CHAPTER ${index + 1} OF ${T.chapters.length}`;
    $('panelTitle').textContent = ch.english;
    $('panelNative').textContent = ch.native;
    $('panelIcon').innerHTML = makeIcon(ch.icon);

    railItems.forEach((el, i) => {
      el.classList.toggle('done', i < index);
      el.classList.toggle('current', i === index);
    });
  }

  const graphemeUnits = (text) => {
    const clean = String(text).replace(/\s+/g, '');
    if (typeof Intl !== 'undefined' && Intl.Segmenter) {
      const seg = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
      return Array.from(seg.segment(clean), (s) => s.segment);
    }
    return Array.from(clean);
  };

  function layoutTiles(text) {
    const box = $('natText');
    const words = T.language.char_tiles
      ? graphemeUnits(text)
      : String(text).split(/\s+/).filter(Boolean);
    box.dir = T.language.rtl ? 'rtl' : 'ltr';
    box.classList.remove('lines');
    box.style.flexWrap = 'nowrap';
    box.innerHTML = words.map((w) => `<span class="tile"><span class="tile-bg">${esc(w)}</span></span>`).join('');
    const tiles = Array.from(box.querySelectorAll('.tile'));
    const avail = box.clientWidth;
    const natLen = text.length;
    const start = natLen <= 14 ? 108 : natLen <= 24 ? 98 : natLen <= 36 ? 88 : natLen <= 50 ? 78 : natLen <= 72 ? 68 : 60;
    const gap = 6;
    const MIN = 34;

    const lineWidths = (rows) => rows.map((row) => row.reduce((sum, el) => sum + el.offsetWidth, 0) + gap * Math.max(0, row.length - 1));
    const widest = (rows) => Math.max(...lineWidths(rows));

    const split = (count) => {
      if (count === 1) return [tiles];
      let best = null;
      let bestW = Infinity;
      if (count === 2) {
        for (let i = 1; i < tiles.length; i++) {
          const rows = [tiles.slice(0, i), tiles.slice(i)];
          const w = widest(rows);
          if (w < bestW) { bestW = w; best = rows; }
        }
      } else {
        for (let i = 1; i < tiles.length - 1; i++) {
          for (let j = i + 1; j < tiles.length; j++) {
            const rows = [tiles.slice(0, i), tiles.slice(i, j), tiles.slice(j)];
            const w = widest(rows);
            if (w < bestW) { bestW = w; best = rows; }
          }
        }
      }
      return best || [tiles];
    };

    const build = (rows) => {
      box.innerHTML = '';
      if (rows.length === 1) {
        box.classList.remove('lines');
        rows[0].forEach((t) => box.appendChild(t));
      } else {
        box.classList.add('lines');
        for (const row of rows) {
          const line = document.createElement('div');
          line.className = 'tile-line';
          row.forEach((t) => line.appendChild(t));
          box.appendChild(line);
        }
      }
    };

    let fitted = false;
    for (const count of [1, 2, 3, 4]) {
      if (tiles.length < count) break;
      box.style.fontSize = start + 'px';
      let rows = split(count);
      let size = start;
      const w0 = widest(rows);
      if (w0 > avail && avail > 0) size = Math.max(MIN, Math.floor(start * (avail / w0) * 0.98));
      while (size >= MIN) {
        box.style.fontSize = size + 'px';
        rows = split(count);
        if (widest(rows) <= avail + 0.5) { build(rows); fitted = true; break; }
        size -= 2;
      }
      if (fitted) break;
    }
    if (!fitted) {
      box.style.fontSize = MIN + 'px';
      build(split(tiles.length >= 4 ? 4 : 3));
    }
    viTiles = Array.from(box.querySelectorAll('.tile'));
  }

  function fitEnText(text) {
    const el = $('enText');
    let size = text.length <= 26 ? 64 : text.length <= 44 ? 58 : text.length <= 64 ? 50 : 44;
    el.style.fontSize = size + 'px';
    while (size > 34 && (el.scrollWidth > el.clientWidth + 1 || el.offsetHeight > 232)) {
      size -= 2;
      el.style.fontSize = size + 'px';
    }
  }

  function fitTranslit(text) {
    const el = $('translitText');
    if (!text) return;
    let size = text.length <= 30 ? 30 : text.length <= 48 ? 26 : 22;
    el.style.fontSize = size + 'px';
    while (size > 19 && el.offsetHeight > size * 2.4) {
      size -= 1;
      el.style.fontSize = size + 'px';
    }
  }

  function fitStack() {
    const stack = $('phraseStack');
    stack.classList.remove('tight');
    const content = Array.from(stack.children).reduce((h, el) => {
      const cs = getComputedStyle(el);
      return h + el.offsetHeight + (parseFloat(cs.marginTop) || 0) + (parseFloat(cs.marginBottom) || 0);
    }, 0);
    if (content > stack.clientHeight - 6) stack.classList.add('tight');
  }

  function setPhrase(p) {
    if (!p || currentPhrase === p.index) return;
    currentPhrase = p.index;
    enActive = -1;
    viActive = -1;

    const ch = T.chapters[p.chapter];
    if (currentChapter !== p.chapter) {
      currentChapter = p.chapter;
      applyChapter(ch, p.chapter);
    }

    const enWords = p.english.split(/\s+/);
    $('enText').innerHTML = enWords.map((w) => `<span class="w"><span class="w-bg">${esc(w)}</span></span>`).join(' ');
    enSpans = Array.from($('enText').querySelectorAll('.w'));
    fitEnText(p.english);

    layoutTiles(p.native);

    $('translitText').textContent = p.transliteration || '';
    $('translit').style.display = p.transliteration ? 'flex' : 'none';
    fitTranslit(p.transliteration || '');
    fitStack();

    const gw = $('ghostWord');
    gw.textContent = p.native;
    gw.style.fontSize = Math.min(300, Math.round(1520 / Math.max(6, p.native.length * 0.52))) + 'px';

    stackHeights = {
      conn: flowHeight($('connector')),
      nat: flowHeight($('natCard')),
      translit: flowHeight($('translit')),
      repeat: flowHeight($('repeatPill')),
    };
    bookSignature = null;
  }

  function wordIndex(words, t) {
    if (!words || !words.length) return -1;
    let idx = -1;
    for (let i = words.length - 1; i >= 0; i--) {
      if (t >= words[i].t0) { idx = i; break; }
    }
    if (idx < 0) return -1;
    const w = words[idx];
    const next = words[idx + 1];
    const end = next ? Math.min(w.t1 + 0.25, next.t0 + 0.1) : w.t1 + 0.35;
    return t <= end ? idx : -1;
  }

  function setActive(spans, idx, prev) {
    if (idx === prev) return prev;
    if (prev >= 0 && spans[prev]) spans[prev].classList.remove('on');
    if (idx >= 0 && spans[idx]) spans[idx].classList.add('on');
    return idx;
  }

  function animateEq(el, t, on) {
    if (!el) return;
    const bars = el.children;
    for (let i = 0; i < bars.length; i++) {
      bars[i].style.height = (on ? 8 + 16 * Math.abs(Math.sin(t * 7.5 + i * 1.25)) : 6).toFixed(1) + 'px';
    }
  }

  function updateMap(p, t) {
    const dots = Array.from($('mapDots').children);
    dots.forEach((dot, i) => {
      const n = i + 1;
      const done = n < p.number || (n === p.number && t >= p.vi_repeat_end);
      const current = n === p.number && !done;
      dot.classList.toggle('done', done);
      dot.classList.toggle('current', current);
      dot.style.transform = current ? `scale(${(1.18 + 0.06 * Math.sin(t * 5)).toFixed(3)})` : '';
    });
  }

  function updateBook(p, t, index) {
    const learned = T.phrases.filter((item, i) =>
      i < index || (i === index && t >= item.vi_repeat_end)
    ).slice(-3);
    const sig = learned.map((x) => x.index).join(',');
    if (sig === bookSignature) return;
    bookSignature = sig;
    if (!learned.length) {
      $('bookList').innerHTML = '<div class="book-empty">Your first phrase lands here…</div>';
      return;
    }
    $('bookList').innerHTML = learned.map((item) => `
      <div class="book-row">
        <span class="b-check">${makeIcon('check')}</span>
        <span class="b-text">${esc(item.english)}</span>
        <span class="b-native">${esc(item.native)}</span>
      </div>`).join('');
  }

  /* ------------------------------------------------------------------ intro */

  function renderIntro(t) {
    const exit = seg(t, T.intro.end - 0.7, T.intro.end);
    $('sceneIntro').style.transform = `translateY(${-34 * exit}px)`;
    op($('sceneIntro'), 1 - exit);

    const a = seg(t, 0.15, 0.65);
    tf($('introEyebrow'), 0, (1 - easeOutBack(a)) * 30, 1, 0);
    op($('introEyebrow'), clamp01(a * 1.8));

    letters.forEach((sp, i) => {
      const p = seg(t, 0.45 + i * 0.05, 0.85 + i * 0.05);
      tf(sp, 0, (1 - easeOutCubic(p)) * 64, 1, 0);
      op(sp, p);
    });

    const lg = seg(t, 1.0, 1.35);
    tf($('logoLang'), 0, (1 - easeOutBack(lg)) * 30, lg > 0 ? easeOutBack(lg) : 0.001, 0);
    op($('logoLang'), clamp01(lg * 1.7));

    const tg = seg(t, 1.2, 1.55);
    tf($('introTag'), 0, (1 - easeOutCubic(tg)) * 24, 1, 0);
    op($('introTag'), tg);

    const st = seg(t, 1.45, 1.8);
    tf($('introStats'), 0, (1 - easeOutCubic(st)) * 20, 1, 0);
    op($('introStats'), st);

    Array.from($('introChips').children).forEach((chip, i) => {
      const p = seg(t, 1.7 + i * 0.09, 2.05 + i * 0.09);
      tf(chip, 0, (1 - easeOutBack(p)) * 26, 1, 0);
      op(chip, clamp01(p * 1.8));
    });

    const ct = seg(t, 2.2, 2.55);
    const pulse = ct >= 1 ? 1 + 0.018 * Math.sin((t - 2.2) * 4.2) : 1;
    tf($('introCta'), 0, (1 - easeOutBack(ct)) * 34, (ct > 0 ? easeOutBack(ct) : 0.001) * pulse, 0);
    op($('introCta'), clamp01(ct * 1.6));

    floatCards.forEach((card, i) => {
      const p = seg(t, 2.35 + i * 0.24, 2.75 + i * 0.24);
      const dx = Math.sin(t * 0.8 + i * 1.9) * 10;
      const dy = (1 - easeOutCubic(p)) * 44 + Math.cos(t * 0.7 + i) * 8;
      const r = (i === 1 ? 5 : i === 2 ? -3 : -6);
      tf(card, dx, dy, p > 0 ? 0.9 + 0.1 * easeOutBack(p) : 0.001, r + Math.sin(t * 0.6 + i) * 1.4);
      op(card, clamp01(p * 1.5));
    });

    const mi = seg(t, 1.8, 2.7);
    const mx = (1 - easeOutCubic(mi)) * 420;
    tf($('introMascot'), mx, (1 - easeOutBack(mi)) * 120, 0.86 + 0.14 * easeOutCubic(mi), (1 - easeOutCubic(mi)) * -14);
    op($('introMascot'), clamp01(mi * 1.8));
    animMascot($('introMascot'), t, { phase: 0.4, wave: mi >= 1 ? 0.75 + 0.25 * Math.sin(t * 1.6) : 0 });

    const ringT = t * 16;
    document.querySelector('.orbit-ring.r1').style.transform = `rotate(${ringT}deg)`;
    document.querySelector('.orbit-ring.r2').style.transform = `rotate(${-ringT * 1.4}deg)`;
  }

  /* ---------------------------------------------------------------- chapter */

  function chapterAt(t) {
    for (const ch of T.chapters) {
      if (t >= ch.intro_start && t < ch.intro_end) return ch;
    }
    return null;
  }

  let chapterShown = -1;

  function setChapterIntro(ch) {
    if (!ch || chapterShown === ch.index) return;
    chapterShown = ch.index;
    applyChapter(ch, ch.index);
    const words = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN'];
    $('chapterNum').textContent = pad2(ch.index + 1);
    $('chapterRibbon').textContent = `CHAPTER ${words[ch.index] || pad2(ch.index + 1)}`;
    $('chapterEyebrow').textContent = `CHAPTER ${ch.index + 1} OF ${T.chapters.length}`;
    $('chapterTitle').textContent = ch.english;
    $('chapterTitle').style.fontSize = (ch.english.length > 13 ? 82 : ch.english.length > 9 ? 96 : 112) + 'px';
    const nativeEl = $('chapterNative');
    nativeEl.textContent = ch.native;
    fitChapterNative(nativeEl);
    const secs = Math.round((ch.phrase_end - ch.phrase_start));
    $('chapterMeta').textContent = `${ch.count} phrases · about ${Math.max(1, Math.round(secs / 60))} minute${secs >= 90 ? 's' : ''}`;
    $('chapterIcon').innerHTML = makeIcon(ch.icon);

    const previewPhrases = T.phrases.slice(ch.first_phrase, ch.first_phrase + 4);
    $('chapterPreviewList').innerHTML = previewPhrases.map((p, i) => `
      <div class="preview-row">
        <span class="preview-num">${i + 1}</span>
        <span class="preview-copy">
          <span class="preview-en">${esc(p.english)}</span>
          <span class="preview-native">${esc(p.native)}</span>
        </span>
      </div>`).join('') + (ch.count > 4 ? `<div class="preview-more">+ ${ch.count - 4} MORE PHRASES</div>` : '');

    $('mapDots').innerHTML = Array.from({ length: ch.count }, () => '<span class="map-dot"></span>').join('');

    const sameName = ch.native.toLowerCase() === ch.english.toLowerCase();
    $('catText').textContent = sameName ? ch.english : `${ch.english} · ${ch.native}`;
  }

  function fitChapterNative(el) {
    const max = el.parentElement ? el.parentElement.clientWidth - 70 : 660;
    el.style.whiteSpace = 'nowrap';
    let size = 40;
    el.style.fontSize = size + 'px';
    while (size > 22 && el.scrollWidth > max) {
      size -= 2;
      el.style.fontSize = size + 'px';
    }
    if (el.scrollWidth > max) el.style.whiteSpace = 'normal';
  }

  function renderChapter(ch, t) {
    const u = t - ch.intro_start;
    const D = ch.intro_end - ch.intro_start;
    const exit = seg(u, D - 0.85, D);

    const washIn = easeOutCubic(seg(u, 0, 0.6));
    const wash = $('chapterWash');
    wash.style.transform = `scaleX(${Math.max(0.001, washIn)}) translateX(${exit * 18}%)`;
    op(wash, (0.10 + 0.05 * washIn) * (1 - exit));

    const card = $('chapterCard');
    const c = seg(u, 0.1, 0.75);
    tf(card, 0, (1 - easeOutBack(c)) * 150 - exit * 80, 0.94 + 0.06 * easeOutCubic(c), 0);
    op(card, clamp01(c * 1.5) * (1 - exit));

    const num = seg(u, 0.25, 0.75);
    tf($('chapterNum'), -(1 - easeOutBack(num)) * 90, 0, 0.7 + 0.3 * easeOutBack(num), 0);
    op($('chapterNum'), clamp01(num * 1.5));

    const ic = seg(u, 0.65, 1.05);
    tf($('chapterIcon'), 0, 0, ic > 0 ? easeOutBack(ic) : 0.001, 0);
    op($('chapterIcon'), clamp01(ic * 1.8));

    const eyebrow = seg(u, 0.75, 1.0);
    tf($('chapterEyebrow'), (1 - easeOutCubic(eyebrow)) * 24, 0, 1, 0);
    op($('chapterEyebrow'), eyebrow);

    const title = seg(u, 0.8, 1.2);
    tf($('chapterTitle'), 0, (1 - easeOutCubic(title)) * 34, 1, 0);
    op($('chapterTitle'), title);

    const nat = seg(u, 0.95, 1.3);
    tf($('chapterNative'), 0, (1 - easeOutCubic(nat)) * 22, 1, 0);
    op($('chapterNative'), nat);

    const meta = seg(u, 1.1, 1.45);
    tf($('chapterMeta'), 0, (1 - easeOutBack(meta)) * 18, meta > 0 ? easeOutBack(meta) : 0.001, 0);
    op($('chapterMeta'), meta);

    Array.from($('chapterSample').children).forEach((chip, i) => {
      const p = seg(u, 1.45 + i * 0.1, 1.8 + i * 0.1);
      tf(chip, 0, (1 - easeOutBack(p)) * 20, 1, 0);
      op(chip, clamp01(p * 1.7));
    });

    Array.from($('chapterPreviewList').children).forEach((row, i) => {
      const p = seg(u, 1.2 + i * 0.13, 1.55 + i * 0.13);
      tf(row, (1 - easeOutCubic(p)) * 30, 0, 1, 0);
      op(row, clamp01(p * 1.7));
    });

    $('chapterWash').style.background = `linear-gradient(100deg, ${ch.accent} 0%, ${shade(ch.accent, -0.28)} 100%)`;
  }

  /* ----------------------------------------------------------------- phrase */

  function renderPhrase(p, t) {
    const u = t - p.start;
    const exit = seg(t, p.end - 0.4, p.end);

    const a = seg(u, 0, 0.55);
    tf($('enCard'), 0, (1 - easeOutBack(a)) * 120 - exit * 40, 0.965 + 0.035 * easeOutCubic(a), 0);
    op($('enCard'), clamp01(a * 1.8) * (1 - exit));

    const c = seg(u, 0.2, 0.55);
    tf($('connector'), 0, 0, c > 0 ? easeOutBack(c) : 0.001, 0);
    op($('connector'), clamp01(c * 2) * (1 - exit));

    const nr = p.nat_reveal;
    const n = seg(t, nr, nr + 0.6);
    tf($('natCard'), 0, (1 - easeOutBack(n)) * 110 - exit * 50, 0.8 + 0.2 * easeOutBack(n), (1 - easeOutCubic(n)) * -2.5);
    op($('natCard'), clamp01(n * 1.6) * (1 - exit));

    for (let i = 0; i < viTiles.length; i++) {
      const s = seg(t, nr + 0.08 + i * 0.045, nr + 0.5 + i * 0.045);
      tf(viTiles[i], 0, (1 - easeOutBack(s)) * 32, 1, 0);
      op(viTiles[i], clamp01(s * 2));
    }

    enActive = setActive(enSpans, wordIndex(p.en_words, t), enActive);
    let viIdx = wordIndex(p.vi_words, t);
    if (viIdx < 0 && p.vi_words_repeat) viIdx = wordIndex(p.vi_words_repeat, t);
    viActive = setActive(viTiles, viIdx, viActive);

    const enPlaying = t >= p.en_start - 0.05 && t <= p.en_end + 0.05;
    $('enLabel').classList.toggle('playing', enPlaying);
    animateEq($('enEq'), t, enPlaying);

    const inRepeat = t >= p.vi_repeat_start - 0.1 && t <= p.vi_repeat_end + 0.1;
    const viPlaying =
      (t >= p.vi_start - 0.05 && t <= p.vi_end + 0.05) || inRepeat;
    $('natLabel').classList.toggle('playing', viPlaying);
    $('natCard').classList.toggle('turn', inRepeat);
    animateEq($('natEq'), t, viPlaying);

    const tr = p.transliteration ? seg(t, nr + 0.3, nr + 0.75) : 0;
    tf($('translit'), 0, (1 - easeOutCubic(tr)) * 18 - exit * 30, 1, 0);
    op($('translit'), tr * (1 - exit));
    $('translit').classList.toggle('echo', inRepeat);

    const rpStart = p.vi_repeat_start - 0.4;
    const rp = seg(t, rpStart, rpStart + 0.5);
    const rpPulse = rp >= 1 ? 1 + 0.022 * Math.sin((t - rpStart) * 4.5) : 1;
    tf($('repeatPill'), 0, (1 - easeOutBack(rp)) * 32 - exit * 24, (rp > 0 ? easeOutBack(rp) : 0.001) * rpPulse, 0);
    op($('repeatPill'), clamp01(rp * 1.8) * (1 - exit));

    const smooth = (x) => x * x * (3 - 2 * x);
    const hidden =
      (1 - smooth(clamp01(c))) * stackHeights.conn +
      (1 - smooth(clamp01(n))) * stackHeights.nat +
      (1 - smooth(clamp01(tr))) * stackHeights.translit +
      (1 - smooth(clamp01(rp))) * stackHeights.repeat;
    $('phraseStack').style.transform = `translateY(${(hidden * 0.5).toFixed(1)}px)`;

    const pm = seg(t, nr, nr + 0.6);
    tf($('peekMascot'), 0, (1 - easeOutBack(pm)) * 70, 0.6 + 0.4 * easeOutBack(pm), 5 * (1 - easeOutCubic(pm)));
    op($('peekMascot'), clamp01(pm * 1.6));
    animMascot($('peekMascot'), t, {
      phase: 1.7,
      wave: pm >= 1 ? 0.55 + 0.3 * Math.sin(t * 1.6) : 0,
      jump: Math.max(0, 1 - Math.abs(t - nr - 0.12) / 0.22),
    });

    const ch = T.chapters[p.chapter];
    const local = seg(t, p.start, p.vi_repeat_end);
    const frac = clamp01((p.number - 1 + local) / Math.max(1, ch.count));
    $('ringFill').style.strokeDashoffset = (728.85 * (1 - frac)).toFixed(2);
    $('ringCount').textContent = `${pad2(p.number)}/${pad2(ch.count)}`;

    updateMap(p, t);
    updateBook(p, t, p.index);
  }

  /* ------------------------------------------------------------------ outro */

  function renderOutro(t) {
    const o = t - T.outro.start;
    const end = T.outro.end - T.outro.start;
    const exit = seg(o, end - 1.0, end);
    $('sceneOutro').style.transform = `translateY(${-30 * exit}px)`;
    op($('sceneOutro'), 1 - exit);

    const c = seg(o, 0, 0.65);
    tf($('outroCard'), 0, (1 - easeOutBack(c)) * 190, 0.94 + 0.06 * easeOutCubic(c), 0);
    op($('outroCard'), clamp01(c * 1.5));

    const b = seg(o, 0.15, 0.7);
    tf($('outroBadge'), 0, 0, b > 0 ? easeOutBack(b) : 0.001, 0);
    op($('outroBadge'), clamp01(b * 2));

    const e = seg(o, 0.3, 0.65);
    tf($('outroEyebrow'), 0, (1 - easeOutCubic(e)) * 18, 1, 0);
    op($('outroEyebrow'), e);

    const ti = seg(o, 0.4, 0.85);
    tf($('outroTitle'), 0, (1 - easeOutCubic(ti)) * 26, 1, 0);
    op($('outroTitle'), ti);

    const sb = seg(o, 0.55, 0.95);
    tf($('outroSub'), 0, (1 - easeOutCubic(sb)) * 20, 1, 0);
    op($('outroSub'), sb);

    Array.from($('outroStats').children).forEach((stat, i) => {
      const s = seg(o, 0.75 + i * 0.12, 1.1 + i * 0.12);
      tf(stat, 0, (1 - easeOutBack(s)) * 22, s > 0 ? easeOutBack(s) : 0.001, 0);
      op(stat, clamp01(s * 1.6));
    });

    Array.from($('outroRecap').children).forEach((chip, i) => {
      const s = seg(o, 1.05 + i * 0.08, 1.4 + i * 0.08);
      tf(chip, 0, (1 - easeOutBack(s)) * 18, 1, 0);
      op(chip, clamp01(s * 1.7));
    });

    const ct = seg(o, 1.6, 2.0);
    const ctp = ct >= 1 ? 1 + 0.018 * Math.sin((o - 1.6) * 4.2) : 1;
    tf($('cta'), 0, (1 - easeOutBack(ct)) * 26, (ct > 0 ? easeOutBack(ct) : 0.001) * ctp, 0);
    op($('cta'), clamp01(ct * 1.6));

    const mc = seg(o, 0.5, 1.2);
    tf($('outroMascot'), 0, (1 - easeOutBack(mc)) * 60, 0.7 + 0.3 * easeOutBack(mc), 0);
    op($('outroMascot'), clamp01(mc * 1.4));
    animMascot($('outroMascot'), t, {
      phase: 2.3,
      wave: mc >= 1 ? 0.8 + 0.2 * Math.sin(t * 2.0) : 0,
      jump: 0.6 * Math.max(0, Math.sin(o * 3.6)),
    });
  }

  /* -------------------------------------------------------------------- HUD */

  function renderHud(t, scene) {
    const show = scene.type === 'intro' ? seg(t, T.intro.end - 1.0, T.intro.end - 0.5) : 1;
    $('hud').style.opacity = String(show);
    $('hud').style.transform = `translateY(${(1 - show) * -14}px)`;
    $('foot').style.opacity = String(scene.type === 'intro' ? seg(t, 2.6, 3.2) * 0.92 : 0.92);

    const pct = scene.type === 'outro' ? 1 : clamp01(t / T.outro.start);
    $('progressFill').style.width = (pct * 100).toFixed(2) + '%';
    const knob = $('progressKnob');
    knob.style.left = (pct * 100).toFixed(2) + '%';
    knob.style.opacity = pct > 0.004 ? '1' : '0';

    $('xpVal').textContent = `${Math.round(pct * T.xp)} XP`;

    let phrase = scene.phrase;
    if (!phrase) {
      if (scene.type === 'outro') phrase = T.phrases[T.phrases.length - 1];
      else {
        const nextIdx = T.phrases.findIndex((p) => p.start > t);
        phrase = T.phrases[Math.max(0, nextIdx - 1)];
      }
    }
    $('phrasePill').textContent = `PHRASE ${phrase.number} / ${T.chapters[phrase.chapter].count}`;

    T.chapters.forEach((ch, i) => {
      const fill = railItems[i].querySelector('.rail-fill');
      let frac = 0;
      if (t >= ch.phrase_end) frac = 1;
      else if (t >= ch.phrase_start) frac = clamp01((t - ch.phrase_start) / Math.max(0.001, ch.phrase_end - ch.phrase_start));
      fill.style.width = (frac * 100).toFixed(2) + '%';
      railItems[i].classList.toggle('done', t >= ch.phrase_end);
      railItems[i].classList.toggle('current', t >= ch.intro_start && t < ch.phrase_end && t < T.outro.start);
    });
  }

  /* ------------------------------------------------------------------- seek */

  let activeScene = '';
  function showScene(name) {
    if (activeScene === name) return;
    activeScene = name;
    $('sceneIntro').classList.toggle('active', name === 'intro');
    $('sceneChapter').classList.toggle('active', name === 'chapter');
    $('scenePhrase').classList.toggle('active', name === 'phrase');
    $('sceneOutro').classList.toggle('active', name === 'outro');
  }

  function phraseAt(t) {
    for (const p of T.phrases) if (t >= p.start && t < p.end) return p;
    return T.phrases[T.phrases.length - 1];
  }

  function seek(t) {
    t = Math.max(0, Math.min(T.duration, t));
    if (t < T.intro.end) {
      showScene('intro');
      renderIntro(t);
      renderHud(t, { type: 'intro' });
    } else if (t >= T.outro.start) {
      showScene('outro');
      renderOutro(t);
      renderHud(t, { type: 'outro' });
    } else {
      const ch = chapterAt(t);
      if (ch) {
        showScene('chapter');
        setChapterIntro(ch);
        renderChapter(ch, t);
        renderHud(t, { type: 'chapter' });
      } else {
        const p = phraseAt(t);
        showScene('phrase');
        setPhrase(p);
        renderPhrase(p, t);
        renderHud(t, { type: 'phrase', phrase: p });
      }
    }
    renderBg(t);
    drawAmbient(t);
    drawTopFx(t);
    window.currentTime = t;
  }

  window.seek = seek;
  window.timeline = T;

  /* ---------------------------------------------------------------- preview */

  function setupPreview(src) {
    const audio = new Audio(src);
    audio.preload = 'auto';
    const bar = document.createElement('div');
    bar.id = 'previewBar';
    bar.innerHTML = `<button id="ppBtn">Play</button><input id="scrub" type="range" min="0" max="${T.duration}" step="0.01" value="0"><span class="ptime" id="ptime">0:00 / ${fmtTime(T.duration)}</span>`;
    document.body.appendChild(bar);
    const btn = bar.querySelector('#ppBtn');
    const scrub = bar.querySelector('#scrub');
    const tm = bar.querySelector('#ptime');
    function tick() {
      if (!audio.paused) {
        seek(audio.currentTime);
        scrub.value = String(audio.currentTime);
        tm.textContent = `${fmtTime(audio.currentTime)} / ${fmtTime(T.duration)}`;
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
    btn.onclick = () => {
      if (audio.paused) {
        audio.play().then(() => { btn.textContent = 'Pause'; }).catch(() => { btn.textContent = 'Tap again to play'; });
      } else {
        audio.pause();
        btn.textContent = 'Play';
      }
    };
    audio.onended = () => { btn.textContent = 'Replay'; };
    scrub.oninput = () => {
      const v = parseFloat(scrub.value);
      audio.currentTime = v;
      seek(v);
      tm.textContent = `${fmtTime(v)} / ${fmtTime(T.duration)}`;
    };
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space') { e.preventDefault(); btn.click(); }
    });
  }

  const ready = () => {
    try { seek(0); } catch (e) { console.error(e); }
    window.sceneReady = true;
    if (window.__AUDIO_SRC__) setupPreview(window.__AUDIO_SRC__);
  };

  const specs = ['900 70px Nunito', '1000 150px Nunito', '800 32px Nunito', 'italic 800 34px Nunito', '900 96px Nunito'];
  Promise.all(specs.map((s) => document.fonts.load(s).catch(() => null)))
    .then(() => document.fonts.ready)
    .then(ready)
    .catch(ready);
})();
