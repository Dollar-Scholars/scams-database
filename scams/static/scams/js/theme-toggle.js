/*
 * Dark-mode toggle, shared with https://dollarscholars.org/ (same localStorage key,
 * markup and labels). The inline script in base.html has already set
 * html[data-theme] before first paint; this script wires up the button.
 *
 * Additions to the site's script:
 *  - after every apply() it dispatches
 *      document.dispatchEvent(new CustomEvent('ds:themechange', {detail: {theme}}))
 *    so charts and other JS-drawn UI can recolour ('light' or 'dark');
 *  - with no stored choice it follows the operating system (prefers-color-scheme).
 */
(() => {
    const key = 'ds.website.theme';
    const root = document.documentElement;
    const button = document.getElementById('ds-theme-toggle');
    const media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

    function stored() {
        try {
            const value = localStorage.getItem(key);
            return value === 'dark' || value === 'light' ? value : null;
        } catch (_) {
            return null;
        }
    }

    function systemTheme() {
        return media && media.matches ? 'dark' : 'light';
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

    apply(root.dataset.theme || stored() || systemTheme());

    if (button) {
        button.addEventListener('click', () => {
            const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
            apply(theme);
            try { localStorage.setItem(key, theme); } catch (_) {}
        });
    }

    // Keep other open tabs of this app in sync.
    window.addEventListener('storage', event => {
        if (event.key === key || event.key === null) {
            apply(event.newValue === 'dark' || event.newValue === 'light' ? event.newValue : systemTheme());
        }
    });

    // Follow the OS setting live until the visitor picks a theme themselves.
    if (media) {
        const onSystemChange = () => {
            if (!stored()) apply(systemTheme());
        };
        if (media.addEventListener) media.addEventListener('change', onSystemChange);
        else if (media.addListener) media.addListener(onSystemChange);
    }
})();
