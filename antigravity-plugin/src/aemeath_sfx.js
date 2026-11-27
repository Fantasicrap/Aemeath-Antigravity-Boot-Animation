(function () {
  class AemeathSfx {
    constructor(audioUrl, initialEnabled = true) {
      this.enabled = initialEnabled;
      this.audio = null;
      this.started = false;
      this.blocked = false;
      if (audioUrl) {
        this.audio = new Audio(audioUrl);
        this.audio.preload = 'auto';
        this.audio.volume = 0.88;
      }
    }

    tryStart(t = 0) {
      if (!this.enabled || !this.audio) return;
      if (t >= 14.3) return;
      try {
        this.audio.currentTime = Math.max(0, Math.min(14.3, t));
        const p = this.audio.play();
        this.started = true;
        if (p && typeof p.catch === 'function') {
          p.catch(() => {
            this.blocked = true;
            this.started = false;
          });
        }
      } catch {
        this.blocked = true;
      }
    }

    unlock(t = 0) {
      if (this.enabled && !this.started && t < 14.0) {
        this.blocked = false;
        this.tryStart(t);
      }
    }

    toggle(t = 0) {
      this.enabled = !this.enabled;
      if (!this.enabled) {
        this.stop();
      } else {
        this.blocked = false;
        this.tryStart(t);
      }
      return this.enabled;
    }

    stop() {
      this.started = false;
      if (this.audio) {
        try {
          this.audio.pause();
          this.audio.currentTime = 0;
        } catch {}
      }
    }

    reset() {
      this.stop();
      if (this.enabled) this.tryStart(0);
    }

    cue(t) {
      if (!this.enabled || !this.audio) return;
      if (!this.started && !this.blocked && t >= 0.02 && t < 13.8) {
        this.tryStart(t);
      }
    }
  }

  window.__AEMEATH_SFX__ = AemeathSfx;
})();
