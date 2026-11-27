(function () {
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const smooth = (a, b, x) => {
    const t = clamp((x - a) / Math.max(1e-5, b - a));
    return t * t * (3 - 2 * t);
  };
  const smoother = (a, b, x) => {
    const t = clamp((x - a) / Math.max(1e-5, b - a));
    return t * t * t * (t * (t * 6 - 15) + 10);
  };

  const INTRO_DURATION = 14.5;
  const MODE_LABELS = {
    a: '方案 A · 电子星海觉醒',
    b: '方案 B · 隧者机兵双形态',
    c: '方案 C · 纸飞机 / 祝福 / 拯救 / 远航星',
  };

  function startDirector() {
    const assets = window.__AEMEATH_ASSETS__ || {};
    const bridge = window.__AEMEATH_BRIDGE__;
    const FX = window.__AEMEATH_FX__;
    const SFX = window.__AEMEATH_SFX__;

    const $ = (s) => document.querySelector(s);
    const stage = $('#stage');
    const cam = $('#cam');
    const layers = [$('#layer-0'), $('#layer-1'), $('#layer-2'), $('#layer-3'), $('#layer-4')];
    const endVeil = $('#end-veil');
    const endBadge = $('#end-badge');
    const endModeLabel = $('#end-mode-label');
    const subtitle = $('#subtitle');
    const subMain = $('#sub-main');
    const subSec = $('#sub-sec');
    const btnBright = $('#btn-bright');
    const btnSfx = $('#btn-sfx');
    const btnReplay = $('#btn-replay');
    const btnSub = $('#btn-sub');
    const modePills = Array.from(document.querySelectorAll('.mode-pill'));

    // Modal controls
    const subModal = $('#sub-modal');
    const chkSubShow = $('#chk-sub-show');
    const inpSubMain = $('#inp-sub-main');
    const inpSubSec = $('#inp-sub-sec');
    const btnSubReset = $('#btn-sub-reset');
    const btnSubCancel = $('#btn-sub-cancel');
    const btnSubSave = $('#btn-sub-save');

    let prefs = bridge.getDefaults();
    const params = new URLSearchParams(window.location.search);
    if (params.has('mode') && ['a', 'b', 'c'].includes(params.get('mode'))) {
      prefs.mode = params.get('mode');
    }

    const fx = new FX($('#fx'));
    const sfx = new SFX(assets.bootAudio || null, prefs.soundEnabled);

    let startTime = performance.now();
    let pinnedAt = params.has('t') ? (parseFloat(params.get('t')) || 0) : null;
    let currentT = 0;
    let finished = false;
    let fading = false;
    let fullBrightMode = false;
    let fadeBlend = 0;
    let mx = 0, my = 0, smx = 0, smy = 0;

    function configureModeLayers(mode) {
      for (const img of layers) {
        img.style.opacity = '0';
        img.style.webkitMaskImage = 'none';
        img.style.maskImage = 'none';
        img.style.filter = 'none';
        img.className = 'layer';
      }
      if (mode === 'a') {
        layers[0].src = assets.a_line || '';
        layers[0].classList.add('layer-add');
        layers[1].src = assets.a_neon || '';
        layers[1].classList.add('layer-add');
        layers[2].src = assets.a_closed || '';
        layers[3].src = assets.a_open || '';
        layers[4].src = assets.a_climax || '';
      } else if (mode === 'b') {
        layers[0].src = assets.b_line || '';
        layers[0].classList.add('layer-add');
        layers[1].src = assets.b_neon || '';
        layers[1].classList.add('layer-add');
        layers[2].src = assets.b_idol || '';
        layers[3].src = assets.b_mecha || '';
        layers[3].classList.add('layer-center');
        layers[4].src = '';
      } else {
        layers[0].src = assets.c_plane || '';
        layers[0].classList.add('layer-center');
        layers[1].src = assets.c_blessing || '';
        layers[2].src = assets.c_salvation || '';
        layers[2].classList.add('layer-center');
        layers[3].src = assets.c_voyager || '';
        layers[4].src = '';
      }
      if (endModeLabel) endModeLabel.textContent = MODE_LABELS[mode] || '';
      modePills.forEach((p) => p.classList.toggle('active', p.dataset.mode === mode));
    }

    function syncButtons() {
      if (btnSfx) btnSfx.textContent = sfx.enabled ? '音乐 开' : '音乐 关';
      if (btnBright) btnBright.textContent = fullBrightMode ? '柔暗收尾' : '全亮观赏';
    }

    function applyFrame(t) {
      currentT = t;
      const mode = prefs.mode || 'a';

      const isFading = t >= 12.6;
      if (isFading && !fading) {
        fading = true;
        stage.classList.add('is-fading');
      } else if (!isFading && fading) {
        fading = false;
        stage.classList.remove('is-fading');
      }

      const done = t >= INTRO_DURATION;
      if (done && !finished) {
        finished = true;
        stage.classList.add('is-done');
      } else if (!done && finished) {
        finished = false;
        stage.classList.remove('is-done');
      }

      const pxActive = smooth(10.5, 12.5, t);
      smx += (mx * pxActive - smx) * 0.08;
      smy += (my * pxActive - smy) * 0.08;

      const outroCurve = smoother(12.60, INTRO_DURATION, t);
      const targetFade = fullBrightMode ? 0 : outroCurve;
      fadeBlend = pinnedAt !== null ? targetFade : fadeBlend + (targetFade - fadeBlend) * 0.08;

      // Subtle cinematic camera breathing + climax zoom kick
      let extraScale = 0;
      if (mode === 'b' && t >= 10.45 && t < 12.60) {
        extraScale = 0.065 * (1 - smoother(10.45, 12.60, t));
      } else if (mode === 'c' && t >= 8.95 && t < 10.65) {
        extraScale = 0.055 * (1 - smoother(8.95, 10.65, t));
      }
      const breathScale =
        1.0 +
        extraScale +
        0.011 * Math.sin(t * 0.785) * smooth(1.6, 4.5, t) +
        0.018 * (1 - smooth(0, 10.5, t)) +
        0.042 * fadeBlend;

      // Glitch micro-jitter around 8.85..10.45s
      let gx = 0, gy = 0;
      if ((mode === 'a' && ((t >= 8.85 && t <= 9.28) || (t >= 10.05 && t <= 10.45))) ||
          (mode === 'b' && (t >= 8.85 && t <= 10.45)) ||
          (mode === 'c' && ((t >= 8.65 && t <= 9.35) || (t >= 10.05 && t <= 10.45)))) {
        const amp = mode === 'b' ? 7.5 : 4.2;
        gx = Math.sin(t * 97.3) * amp;
        gy = Math.cos(t * 73.1) * (amp * 0.45);
      }

      const dx = -smx * 10 + Math.sin(t * 0.62) * 3.0 * smooth(2.0, 5.0, t) + gx;
      const dy = -smy * 7 + Math.cos(t * 0.52) * 2.2 * smooth(2.0, 5.0, t) + gy;
      cam.style.transform = `translate3d(${dx.toFixed(2)}px,${dy.toFixed(2)}px,0) scale(${breathScale.toFixed(4)})`;

      cam.style.opacity = (1 - fadeBlend * 0.85).toFixed(3);
      cam.style.filter = fadeBlend > 0.004
        ? `brightness(${(1 - fadeBlend * 0.30).toFixed(3)}) blur(${(fadeBlend * 2.8).toFixed(2)}px)`
        : 'none';
      if (endVeil) endVeil.style.opacity = (fadeBlend * 0.90).toFixed(3);

      const badgeCurve = smoother(13.35, 14.55, t);
      const badgeOp = badgeCurve * fadeBlend;
      if (endBadge) {
        endBadge.style.opacity = badgeOp.toFixed(3);
        endBadge.style.transform = `translate3d(-50%,calc(-50% + ${((1 - badgeCurve) * 8).toFixed(1)}px),0)`;
      }

      fx.render(mode, t, smx, smy, fadeBlend);
      sfx.cue(t);

      // Mode-specific layer blending (all synced to 14.5s《于电子星海轻歌》)
      if (mode === 'a') {
        const rPct = 14 + smooth(0.0, 2.20, t) * 20 + smooth(2.20, 4.35, t) * 96;
        const maskVal = `radial-gradient(circle at 50% 45%, #000 ${Math.max(0, rPct - 12).toFixed(1)}%, transparent ${rPct.toFixed(1)}%)`;
        const opLine = smooth(0.10, 0.90, t) * (1 - smooth(3.10, 4.55, t));
        const opNeon = smooth(2.10, 4.10, t) * (1 - smooth(4.45, 5.30, t));
        const opClosed = smooth(4.45, 5.20, t) * (1 - smooth(9.10, 9.75, t));
        const opOpen = smooth(9.10, 9.75, t) * (1 - smooth(10.45, 11.20, t));
        const opClimax = smooth(10.45, 11.20, t);

        layers[0].style.opacity = opLine.toFixed(3);
        layers[0].style.webkitMaskImage = maskVal;
        layers[0].style.maskImage = maskVal;
        layers[1].style.opacity = opNeon.toFixed(3);
        layers[1].style.webkitMaskImage = maskVal;
        layers[1].style.maskImage = maskVal;
        layers[2].style.opacity = opClosed.toFixed(3);
        layers[3].style.opacity = opOpen.toFixed(3);
        layers[4].style.opacity = opClimax.toFixed(3);
      } else if (mode === 'b') {
        const syPct = smooth(0.05, 4.10, t) * 112;
        const scanMask = `linear-gradient(to bottom, #000 ${Math.max(0, syPct - 10).toFixed(1)}%, transparent ${syPct.toFixed(1)}%)`;
        const opLine = smooth(0.08, 0.80, t) * (1 - smooth(3.10, 4.50, t));
        const opNeon = smooth(1.90, 4.15, t) * (1 - smooth(4.45, 5.15, t));
        const useMechaFlash = (t >= 9.34 && t <= 9.54) || t >= 10.12;
        const opIdol = smooth(4.45, 5.05, t) * (useMechaFlash ? 0 : 1);
        const opMecha = useMechaFlash ? 1 : 0;

        layers[0].style.opacity = opLine.toFixed(3);
        layers[0].style.webkitMaskImage = scanMask;
        layers[0].style.maskImage = scanMask;
        layers[1].style.opacity = opNeon.toFixed(3);
        layers[1].style.webkitMaskImage = scanMask;
        layers[1].style.maskImage = scanMask;
        layers[2].style.opacity = opIdol.toFixed(3);
        layers[3].style.opacity = opMecha.toFixed(3);
        layers[4].style.opacity = '0';
      } else {
        // Mode C: Paper Plane (0..4.55) -> Blessing (4.15..8.95) -> Salvation (8.95..12.65) -> Voyager (12.05..14.5+)
        const opPlane = smoother(0.0, 1.35, t) * (1 - smooth(4.15, 4.55, t));
        const opBless = smooth(4.15, 4.55, t) * (t < 8.95 ? 1 : 0);
        const opSalv = (t >= 8.95 ? 1 : 0) * (1 - smoother(12.05, 12.65, t));
        const opVoy = smoother(12.05, 12.65, t);
        layers[0].style.opacity = opPlane.toFixed(3);
        layers[1].style.opacity = opBless.toFixed(3);
        layers[2].style.opacity = opSalv.toFixed(3);
        layers[3].style.opacity = opVoy.toFixed(3);
        layers[4].style.opacity = '0';
      }

      // Customizable CJK Serif Subtitle (4.65s .. 12.65s)
      if (prefs.showSubtitle && (prefs.subtitlePrimary || '').trim()) {
        const subIn = smooth(4.65, 5.10, t);
        const subOut = 1 - smooth(12.15, 12.65, t);
        const opSub = subIn * subOut;
        if (opSub > 0.005) {
          subMain.textContent = prefs.subtitlePrimary;
          subSec.textContent = prefs.subtitleSecondary || '';
          subSec.style.display = (prefs.subtitleSecondary || '').trim() ? 'block' : 'none';
          subtitle.style.opacity = opSub.toFixed(3);
          subtitle.style.transform = `translate3d(-50%,${((1 - subIn) * 7).toFixed(1)}px,0)`;
        } else {
          subtitle.style.opacity = '0';
        }
      } else {
        subtitle.style.opacity = '0';
      }
    }

    function skipToEnd() {
      pinnedAt = null;
      sfx.stop();
      startTime = performance.now() - INTRO_DURATION * 1000;
      applyFrame(INTRO_DURATION);
    }

    function replay() {
      pinnedAt = null;
      finished = false;
      fading = false;
      fullBrightMode = false;
      fadeBlend = 0;
      stage.classList.remove('is-done', 'is-fading');
      configureModeLayers(prefs.mode);
      syncButtons();
      startTime = performance.now();
      sfx.reset();
      applyFrame(0);
    }

    function switchMode(mode, shouldPersist = true) {
      if (!['a', 'b', 'c'].includes(mode)) return;
      prefs.mode = mode;
      if (shouldPersist) bridge.persistPrefs(prefs);
      replay();
    }

    function openSubModal() {
      chkSubShow.checked = !!prefs.showSubtitle;
      inpSubMain.value = prefs.subtitlePrimary || '';
      inpSubSec.value = prefs.subtitleSecondary || '';
      subModal.classList.add('open');
      stage.classList.add('modal-open');
      setTimeout(() => inpSubMain.focus(), 30);
    }

    function closeSubModal() {
      subModal.classList.remove('open');
      stage.classList.remove('modal-open');
    }

    bridge.onPrefs((remote, shouldReplay) => {
      let changed = false;
      if (remote.mode && ['a', 'b', 'c'].includes(remote.mode) && remote.mode !== prefs.mode) {
        prefs.mode = remote.mode;
        changed = true;
      }
      if (typeof remote.showSubtitle === 'boolean') prefs.showSubtitle = remote.showSubtitle;
      if (typeof remote.subtitlePrimary === 'string') prefs.subtitlePrimary = remote.subtitlePrimary;
      if (typeof remote.subtitleSecondary === 'string') prefs.subtitleSecondary = remote.subtitleSecondary;
      if (typeof remote.soundEnabled === 'boolean') {
        prefs.soundEnabled = remote.soundEnabled;
        sfx.enabled = remote.soundEnabled;
      }
      configureModeLayers(prefs.mode);
      syncButtons();
      if (shouldReplay || changed) replay();
    });
    bridge.init();

    window.addEventListener('pointermove', (e) => {
      mx = (e.clientX / Math.max(1, window.innerWidth) - 0.5) * 2;
      my = (e.clientY / Math.max(1, window.innerHeight) - 0.5) * 2;
    });

    window.addEventListener('keydown', (e) => {
      if (subModal.classList.contains('open')) {
        if (e.key === 'Escape') closeSubModal();
        return;
      }
      if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') {
        if (!finished) skipToEnd();
      } else if (e.key === 'r' || e.key === 'R') {
        replay();
      } else if (e.key === '1') {
        switchMode('a');
      } else if (e.key === '2') {
        switchMode('b');
      } else if (e.key === '3') {
        switchMode('c');
      }
    });

    stage.addEventListener('click', (e) => {
      if (e.target.closest('#controls') || subModal.classList.contains('open')) return;
      if (sfx.blocked && !finished) {
        sfx.unlock(currentT);
        return;
      }
      if (!finished) skipToEnd();
    });

    modePills.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        switchMode(btn.dataset.mode);
      });
    });

    btnBright.addEventListener('click', (e) => {
      e.stopPropagation();
      fullBrightMode = !fullBrightMode;
      syncButtons();
    });

    btnSfx.addEventListener('click', (e) => {
      e.stopPropagation();
      prefs.soundEnabled = sfx.toggle(currentT);
      bridge.persistPrefs(prefs);
      syncButtons();
    });

    btnReplay.addEventListener('click', (e) => {
      e.stopPropagation();
      replay();
    });

    btnSub.addEventListener('click', (e) => {
      e.stopPropagation();
      openSubModal();
    });

    btnSubCancel.addEventListener('click', () => closeSubModal());
    subModal.addEventListener('click', (e) => {
      if (e.target === subModal) closeSubModal();
    });
    btnSubReset.addEventListener('click', () => {
      chkSubShow.checked = true;
      inpSubMain.value = '拯救世界的事，就交给我吧……';
      inpSubSec.value = 'Leave saving the world to me...';
    });
    btnSubSave.addEventListener('click', () => {
      prefs.showSubtitle = chkSubShow.checked;
      prefs.subtitlePrimary = inpSubMain.value;
      prefs.subtitleSecondary = inpSubSec.value;
      bridge.persistPrefs(prefs);
      closeSubModal();
      replay();
    });

    window.__AEMEATH_SEEK__ = (sec, mode) => {
      if (mode && ['a', 'b', 'c'].includes(mode)) {
        prefs.mode = mode;
        configureModeLayers(mode);
      }
      pinnedAt = sec;
      applyFrame(sec);
    };

    configureModeLayers(prefs.mode);
    syncButtons();
    const loop = (now) => {
      const t = pinnedAt !== null ? pinnedAt : (now - startTime) / 1000;
      applyFrame(t);
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startDirector);
  } else {
    startDirector();
  }
})();
