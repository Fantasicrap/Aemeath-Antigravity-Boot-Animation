(function () {
  const LS_KEY = 'aemeath_antigravity_prefs_v1';
  const DEFAULT_PREFS = {
    mode: 'a',
    showSubtitle: true,
    subtitlePrimary: '拯救世界的事，就交给我吧……',
    subtitleSecondary: 'Leave saving the world to me...',
    soundEnabled: true,
  };

  let mcpApp = null;
  let mcpConnected = false;
  let onRemotePrefs = null;

  function loadLocal() {
    try {
      const raw = window.localStorage && window.localStorage.getItem(LS_KEY);
      if (raw) return Object.assign({}, DEFAULT_PREFS, JSON.parse(raw));
    } catch (_) {}
    return Object.assign({}, DEFAULT_PREFS);
  }

  function saveLocal(p) {
    try {
      if (window.localStorage) window.localStorage.setItem(LS_KEY, JSON.stringify(p));
    } catch (_) {}
  }

  const Bridge = {
    getDefaults() {
      return loadLocal();
    },
    onPrefs(cb) {
      onRemotePrefs = cb;
    },
    async persistPrefs(prefs) {
      saveLocal(prefs);
      if (mcpApp && mcpConnected) {
        try {
          await mcpApp.callServerTool({
            name: 'save_aemeath_prefs',
            arguments: {
              mode: prefs.mode,
              showSubtitle: !!prefs.showSubtitle,
              subtitlePrimary: String(prefs.subtitlePrimary || ''),
              subtitleSecondary: String(prefs.subtitleSecondary || ''),
              soundEnabled: !!prefs.soundEnabled,
            },
          });
        } catch (_) {}
      }
    },
    init() {
      if (window.parent === window) return;
      const sdk = window.__MCP_EXT_APPS__;
      if (!sdk || !sdk.App) return;
      try {
        mcpApp = new sdk.App({ name: 'aemeath-intro', version: '1.0.0' }, {});
        mcpApp.ontoolinput = (inp) => {
          if (inp && inp.arguments && onRemotePrefs) {
            onRemotePrefs(inp.arguments, false);
          }
        };
        mcpApp.ontoolresult = (res) => {
          const prefs = res && res.structuredContent && res.structuredContent.prefs;
          if (prefs && onRemotePrefs) onRemotePrefs(prefs, true);
        };
        mcpApp.connect().then(async () => {
          mcpConnected = true;
          try {
            const r = await mcpApp.callServerTool({ name: 'get_aemeath_prefs', arguments: {} });
            const prefs = r && r.structuredContent && r.structuredContent.prefs;
            if (prefs && onRemotePrefs) onRemotePrefs(prefs, false);
          } catch (_) {}
        }).catch(() => {});
      } catch (_) {}
    },
  };

  window.__AEMEATH_BRIDGE__ = Bridge;
})();
