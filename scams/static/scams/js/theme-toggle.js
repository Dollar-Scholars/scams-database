/*
 * Dark-mode toggle, the same as https://dollarscholars.org/'s: same localStorage key,
 * markup and labels, light until the visitor picks dark, and the same ds_theme cookie
 * across *.dollarscholars.org so a choice made on either site shows on both. The inline
 * script in base.html has already set html[data-theme] before first paint; this script
 * wires up the button.
 *
 * Addition to the site's script: after every apply() it dispatches
 *     document.dispatchEvent(new CustomEvent('ds:themechange', {detail: {theme}}))
 * so charts and other JS-drawn UI can recolour ('light' or 'dark').
 */
(() => {
    const key = 'ds.website.theme';
    const root = document.documentElement;
    const button = document.getElementById('ds-theme-toggle');

    // The shared cookie; local development keeps it host-only.
    function readShared() {
        const match = document.cookie.match(/(?:^|;\s*)ds_theme=(dark|light)(?:;|$)/);
        return match ? match[1] : null;
    }

    function writeShared(theme) {
        let cookie = `ds_theme=${theme}; Max-Age=31536000; Path=/; SameSite=Lax`;
        if (/(^|\.)dollarscholars\.org$/.test(location.hostname)) cookie += '; Domain=dollarscholars.org';
        if (location.protocol === 'https:') cookie += '; Secure';
        document.cookie = cookie;
    }

    function apply(theme) {
        const dark = theme === 'dark';
        root.dataset.theme = dark ? 'dark' : 'light';
        root.style.colorScheme = dark ? 'dark' : 'light';
        if (button) {
            // Labels come from data attributes so they can be translated.
            const label = dark
                ? (button.dataset.labelLight || 'Switch to light mode')
                : (button.dataset.labelDark || 'Switch to dark mode');
            button.setAttribute('aria-label', label);
            button.title = label;
        }
        document.dispatchEvent(new CustomEvent('ds:themechange', {
            detail: { theme: dark ? 'dark' : 'light' },
        }));
    }

    apply(root.dataset.theme);

    if (button) {
        button.addEventListener('click', () => {
            const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
            apply(theme);
            try { localStorage.setItem(key, theme); } catch (_) {}
            writeShared(theme);
        });
    }

    // Coming back to this tab after switching on the main site: follow it.
    document.addEventListener('visibilitychange', () => {
        const shared = readShared();
        if (!document.hidden && shared && shared !== root.dataset.theme) apply(shared);
    });

    // Keep other open tabs of this app in sync.
    window.addEventListener('storage', event => {
        if (event.key === key || event.key === null) apply(event.newValue);
    });
})();
