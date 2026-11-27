(function () {
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const smooth = (a, b, x) => {
    const t = clamp((x - a) / Math.max(1e-5, b - a));
    return t * t * (3 - 2 * t);
  };

  class AemeathFX {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.w = 1280;
      this.h = 720;
      this.motes = [];
      this.outroDust = [];
      let seed = 20260314;
      const rand = () => {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        return seed / 4294967296;
      };
      const palettes = ['255,168,218', '132,238,255', '255,232,168'];
      for (let i = 0; i < 72; i++) {
        this.motes.push({
          x: rand(),
          y: rand(),
          r: 0.9 + rand() * 2.2,
          spdY: 0.012 + rand() * 0.024,
          spdX: (rand() - 0.5) * 0.015,
          phase: rand() * Math.PI * 2,
          tw: 1.4 + rand() * 2.5,
          star: rand() > 0.58,
          hue: palettes[i % 3],
        });
      }
      for (let i = 0; i < 50; i++) {
        this.outroDust.push({
          x: 0.14 + rand() * 0.78,
          y0: 0.20 + rand() * 0.68,
          lift: 0.12 + rand() * 0.25,
          drift: (rand() - 0.5) * 0.08,
          delay: rand() * 0.85,
          dur: 1.45 + rand() * 0.85,
          r: 0.8 + rand() * 1.9,
          star: rand() > 0.55,
          hue: palettes[i % 3],
        });
      }
      this.resize();
      window.addEventListener('resize', () => this.resize());
    }

    resize() {
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.w = Math.max(1, this.canvas.clientWidth || window.innerWidth);
      this.h = Math.max(1, this.canvas.clientHeight || window.innerHeight);
      this.canvas.width = Math.round(this.w * this.dpr);
      this.canvas.height = Math.round(this.h * this.dpr);
    }

    imgToScreen(nx, ny, px = 0, py = 0, anchorX = 0.62) {
      const imgAspect = 16 / 9;
      const viewAspect = this.w / this.h;
      let drawW, drawH, offX, offY;
      if (viewAspect > imgAspect) {
        drawW = this.w * 1.06;
        drawH = drawW / imgAspect;
        offX = (this.w - drawW) * anchorX;
        offY = (this.h - drawH) * 0.45;
      } else {
        drawH = this.h * 1.06;
        drawW = drawH * imgAspect;
        offX = (this.w - drawW) * anchorX;
        offY = (this.h - drawH) * 0.45;
      }
      return [offX + nx * drawW + px, offY + ny * drawH + py];
    }

    drawStarFlare(cx, cy, radius, intensity, rgb = '255,176,220', anamorphic = 0, angle = 0) {
      if (intensity <= 0.004) return;
      const ctx = this.ctx;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';

      const halo = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 1.15);
      halo.addColorStop(0, `rgba(255,255,255,${clamp(intensity * 0.9)})`);
      halo.addColorStop(0.20, `rgba(${rgb},${clamp(intensity * 0.65)})`);
      halo.addColorStop(0.52, `rgba(${rgb},${clamp(intensity * 0.22)})`);
      halo.addColorStop(1, `rgba(${rgb},0)`);
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.15, 0, Math.PI * 2);
      ctx.fill();

      ctx.translate(cx, cy);
      ctx.rotate(angle);
      const drawSpike = (len, thick, alpha) => {
        const g = ctx.createLinearGradient(-len, 0, len, 0);
        g.addColorStop(0, `rgba(${rgb},0)`);
        g.addColorStop(0.42, `rgba(${rgb},${clamp(alpha * 0.6)})`);
        g.addColorStop(0.5, `rgba(255,255,255,${clamp(alpha)})`);
        g.addColorStop(0.58, `rgba(${rgb},${clamp(alpha * 0.6)})`);
        g.addColorStop(1, `rgba(${rgb},0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.moveTo(-len, 0);
        ctx.quadraticCurveTo(0, -thick, len, 0);
        ctx.quadraticCurveTo(0, thick, -len, 0);
        ctx.fill();
      };
      drawSpike(radius * 1.4, Math.max(2.4, radius * 0.052), intensity * 0.94);
      ctx.rotate(Math.PI / 2);
      drawSpike(radius * 1.55, Math.max(2.4, radius * 0.052), intensity * 0.96);
      ctx.rotate(Math.PI / 4);
      drawSpike(radius * 0.52, Math.max(1.4, radius * 0.024), intensity * 0.42);
      ctx.rotate(Math.PI / 2);
      drawSpike(radius * 0.52, Math.max(1.4, radius * 0.024), intensity * 0.42);
      ctx.restore();

      if (anamorphic > 0.01) {
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        const bw = this.w * 0.98;
        const bh = Math.max(3, radius * 0.064);
        const ag = ctx.createLinearGradient(cx - bw * 0.5, cy, cx + bw * 0.5, cy);
        ag.addColorStop(0, `rgba(${rgb},0)`);
        ag.addColorStop(0.30, `rgba(${rgb},${clamp(anamorphic * 0.36)})`);
        ag.addColorStop(0.50, `rgba(255,255,255,${clamp(anamorphic * 0.92)})`);
        ag.addColorStop(0.70, `rgba(${rgb},${clamp(anamorphic * 0.36)})`);
        ag.addColorStop(1, `rgba(${rgb},0)`);
        ctx.fillStyle = ag;
        ctx.fillRect(cx - bw * 0.5, cy - bh * 0.5, bw, bh);
        ctx.restore();
      }
    }

    drawHoloScanline(yNorm, intensity) {
      if (intensity <= 0.01 || yNorm < 0 || yNorm > 1) return;
      const ctx = this.ctx;
      const y = yNorm * this.h;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      const g = ctx.createLinearGradient(0, y - 22, 0, y + 22);
      g.addColorStop(0, 'rgba(105,235,255,0)');
      g.addColorStop(0.45, `rgba(255,148,210,${(intensity * 0.42).toFixed(3)})`);
      g.addColorStop(0.5, `rgba(215,252,255,${(intensity * 0.92).toFixed(3)})`);
      g.addColorStop(0.55, `rgba(105,235,255,${(intensity * 0.42).toFixed(3)})`);
      g.addColorStop(1, 'rgba(105,235,255,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, y - 22, this.w, 44);
      ctx.restore();
    }

    drawGlitchOverlay(t, strength) {
      if (strength <= 0.02) return;
      const ctx = this.ctx;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      let s = Math.floor(t * 48) * 2654435761;
      const rnd = () => {
        s = (s * 1664525 + 1013904223) >>> 0;
        return s / 4294967296;
      };
      const bars = Math.floor(4 + strength * 14);
      for (let i = 0; i < bars; i++) {
        const y = rnd() * this.h;
        const h = 1.5 + rnd() * (6 + strength * 14);
        const x = rnd() * this.w * 0.65;
        const w = this.w * (0.2 + rnd() * 0.65);
        const isCyan = rnd() > 0.48;
        ctx.fillStyle = isCyan
          ? `rgba(88,236,255,${(strength * (0.14 + rnd() * 0.25)).toFixed(3)})`
          : `rgba(255,96,184,${(strength * (0.14 + rnd() * 0.25)).toFixed(3)})`;
        ctx.fillRect(x, y, w, h);
      }
      ctx.restore();
    }

    drawOutroDispersion(t, px, py) {
      if (t < 12.2 || t > 15.2) return;
      const ctx = this.ctx;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (const s of this.outroDust) {
        const dp = clamp((t - 12.2 - s.delay) / s.dur);
        if (dp <= 0 || dp >= 1) continue;
        const a = Math.sin(dp * Math.PI) * Math.pow(1 - dp, 0.6) * 0.72;
        const easeUp = 1 - Math.pow(1 - dp, 2.2);
        const sx = (s.x + s.drift * easeUp) * this.w + px * 0.35;
        const sy = (s.y0 - s.lift * easeUp) * this.h + py * 0.35;
        if (s.star) {
          const d = s.r * 3.4;
          ctx.strokeStyle = `rgba(${s.hue},${a.toFixed(3)})`;
          ctx.lineWidth = 0.95;
          ctx.beginPath();
          ctx.moveTo(sx - d, sy); ctx.lineTo(sx + d, sy);
          ctx.moveTo(sx, sy - d); ctx.lineTo(sx, sy + d);
          ctx.stroke();
        }
        ctx.fillStyle = `rgba(${s.hue},${a.toFixed(3)})`;
        ctx.beginPath();
        ctx.arc(sx, sy, s.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    render(mode, t, smx, smy, fadeOut = 0) {
      const ctx = this.ctx;
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      ctx.clearRect(0, 0, this.w, this.h);

      const px = -smx * 12;
      const py = -smy * 8;
      const flareKeep = 1 - fadeOut * 0.82;
      const anchorX = mode === 'b' && t >= 10.12 ? 0.50 : 0.62;
      const minDim = Math.min(this.w, this.h);

      // 1. Drifting pink / cyan / gold digital star motes
      const moteAlpha = smooth(1.0, 3.4, t) * (0.80 - fadeOut * 0.36);
      if (moteAlpha > 0.01) {
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        for (const m of this.motes) {
          const x = ((m.x + t * m.spdX) % 1 + 1) % 1 * this.w + px * 0.55;
          const y = ((m.y - t * m.spdY) % 1 + 1) % 1 * this.h + py * 0.55;
          const tw = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * m.tw + m.phase));
          const a = moteAlpha * tw * 0.85;
          if (m.star && tw > 0.58) {
            const s = m.r * 3.5;
            ctx.strokeStyle = `rgba(${m.hue},${a.toFixed(3)})`;
            ctx.lineWidth = 1.0;
            ctx.beginPath();
            ctx.moveTo(x - s, y); ctx.lineTo(x + s, y);
            ctx.moveTo(x, y - s); ctx.lineTo(x, y + s);
            ctx.stroke();
          }
          ctx.fillStyle = `rgba(${m.hue},${a.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(x, y, m.r, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }

      // 2. Mode-specific audio-synced flares, scanlines & glitches (14.5s timeline, centered official framing)
      if (mode === 'a') {
        if (t >= 1.85 && t <= 4.35) {
          const sp = clamp((t - 1.85) / 2.50);
          this.drawHoloScanline(0.12 + sp * 0.78, Math.sin(sp * Math.PI) * 0.52);
        }
        if (t >= 4.45 && t <= 6.20) {
          const fg = Math.sin(clamp((t - 4.45) / 1.75) * Math.PI);
          const [lx, ly] = this.imgToScreen(0.18, 0.42, px, py, 0.50);
          const [rx, ry] = this.imgToScreen(0.82, 0.42, px, py, 0.50);
          this.drawStarFlare(lx, ly, minDim * 0.24, fg * 0.72, '125,238,255', 0);
          this.drawStarFlare(rx, ry, minDim * 0.24, fg * 0.72, '255,172,216', 0);
        }
        if (t >= 8.85 && t <= 9.25) this.drawGlitchOverlay(t, (1 - smooth(8.85, 9.25, t)) * 0.85);
        if (t >= 10.05 && t <= 10.48) this.drawGlitchOverlay(t, smooth(10.05, 10.45, t) * 0.90);
        if (t >= 10.45 && t <= 12.40) {
          const bp = clamp((t - 10.45) / 1.95);
          const burst = smooth(0.0, 0.14, bp) * Math.pow(1 - smooth(0.14, 1.0, bp), 1.30);
          const [lx, ly] = this.imgToScreen(0.23, 0.34, px, py, 0.50);
          const [rx, ry] = this.imgToScreen(0.77, 0.34, px, py, 0.50);
          const [cx, cy] = this.imgToScreen(0.50, 0.55, px, py, 0.50);
          this.drawStarFlare(lx, ly, minDim * 0.34, burst * 0.88, '130,238,255', 0, bp * 0.06);
          this.drawStarFlare(rx, ry, minDim * 0.34, burst * 0.88, '255,172,216', 0, -bp * 0.06);
          this.drawStarFlare(cx, cy, minDim * 0.16, burst * 0.58, '255,172,216', burst * 0.78);
        }
        const loopIn = smooth(11.4, 12.6, t);
        if (loopIn > 0.01 && flareKeep > 0.01) {
          const pulse = 0.55 + 0.45 * Math.sin(t * 1.57);
          const [lx, ly] = this.imgToScreen(0.24, 0.30, px, py, 0.50);
          const [rx, ry] = this.imgToScreen(0.76, 0.30, px, py, 0.50);
          this.drawStarFlare(lx, ly, minDim * 0.18, loopIn * (0.20 + 0.12 * pulse) * flareKeep, '125,238,255', 0);
          this.drawStarFlare(rx, ry, minDim * 0.18, loopIn * (0.20 + 0.12 * pulse) * flareKeep, '255,178,220', 0);
        }
      } else if (mode === 'b') {
        if (t < 4.45) {
          const sy = smooth(0.05, 4.10, t);
          this.drawHoloScanline(sy, (1 - smooth(3.75, 4.45, t)) * 0.82);
          if ((t >= 2.20 && t <= 2.48) || (t >= 3.85 && t <= 4.15)) this.drawGlitchOverlay(t, 0.45);
        }
        if (t >= 8.85 && t <= 10.48) {
          const gp = clamp((t - 8.85) / 1.63);
          this.drawGlitchOverlay(t, 0.55 + 0.45 * Math.sin(gp * Math.PI) + (t > 10.0 ? 0.35 : 0));
          const fl = smooth(10.18, 10.45, t);
          if (fl > 0.01) {
            ctx.fillStyle = `rgba(255,215,244,${(fl * 0.68).toFixed(3)})`;
            ctx.fillRect(0, 0, this.w, this.h);
          }
        }
        if (t >= 10.45 && t <= 12.40) {
          const bp = clamp((t - 10.45) / 1.95);
          const burst = smooth(0.0, 0.14, bp) * Math.pow(1 - smooth(0.14, 1.0, bp), 1.35);
          const [lx, ly] = this.imgToScreen(0.24, 0.45, px, py, 0.50);
          const [rx, ry] = this.imgToScreen(0.78, 0.45, px, py, 0.50);
          this.drawStarFlare(lx, ly, minDim * 0.30, burst * 0.82, '125,240,255', 0, bp * 0.06);
          this.drawStarFlare(rx, ry, minDim * 0.30, burst * 0.82, '255,148,208', burst * 0.72, -bp * 0.06);
        }
        const loopIn = smooth(11.6, 12.6, t);
        if (loopIn > 0.01 && flareKeep > 0.01) {
          const pulse = 0.55 + 0.45 * Math.sin(t * 1.8);
          const [lx, ly] = this.imgToScreen(0.26, 0.48, px, py, 0.50);
          const [rx, ry] = this.imgToScreen(0.76, 0.48, px, py, 0.50);
          this.drawStarFlare(lx, ly, minDim * 0.16, loopIn * (0.22 + 0.14 * pulse) * flareKeep, '125,240,255', 0);
          this.drawStarFlare(rx, ry, minDim * 0.16, loopIn * (0.22 + 0.14 * pulse) * flareKeep, '255,160,214', 0);
        }
      } else {
        // Mode C: Paper Plane -> Blessing -> Salvation -> Voyager
        if (t >= 8.55 && t <= 9.20) this.drawGlitchOverlay(t, Math.sin(clamp((t - 8.55) / 0.65) * Math.PI) * 0.90);
        if (t >= 10.10 && t <= 10.48) this.drawGlitchOverlay(t, Math.sin(clamp((t - 10.10) / 0.38) * Math.PI) * 0.80);
        if (t >= 10.42 && t <= 12.20) {
          const dp = clamp((t - 10.42) / 1.78);
          const burst = smooth(0.0, 0.14, dp) * Math.pow(1 - smooth(0.14, 1.0, dp), 1.25);
          const [lx, ly] = this.imgToScreen(0.20, 0.36, px, py, 0.50);
          const [rx, ry] = this.imgToScreen(0.82, 0.36, px, py, 0.50);
          this.drawStarFlare(lx, ly, minDim * 0.30, burst * 0.84, '130,242,255', 0);
          this.drawStarFlare(rx, ry, minDim * 0.30, burst * 0.84, '255,224,168', burst * 0.68);
        }
        const loopIn = smooth(12.0, 12.8, t);
        if (loopIn > 0.01 && flareKeep > 0.01) {
          const tw = 0.55 + 0.45 * Math.sin(t * 1.4);
          const [vx, vy] = this.imgToScreen(0.22, 0.26, px, py, 0.50);
          this.drawStarFlare(vx, vy, minDim * 0.22, loopIn * (0.26 + 0.16 * tw) * flareKeep, '255,224,168', 0);
        }
      }

      this.drawOutroDispersion(t, px, py);
    }
  }

  window.__AEMEATH_FX__ = AemeathFX;
})();
