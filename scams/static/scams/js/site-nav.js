/*
 * Mobile navigation (< 1024px): the hamburger button (#site-nav-toggle) shows/hides
 * the header panel (#site-nav-panel) holding the nav links, the "Report a scam"
 * button and the theme toggle.
 * - aria-expanded on the button reflects the state; its label ("Menu", in the page's
 *   language) comes from the template and never changes, so this script has no text
 * - Escape closes the panel and returns focus to the button
 * - clicking a link in the panel, or anywhere outside the header, closes it
 * - widening the window to desktop size resets it
 */
(() => {
    const button = document.getElementById('site-nav-toggle');
    const panel = document.getElementById('site-nav-panel');
    if (!button || !panel) return;

    const header = button.closest('.site-header') || panel.parentElement;
    const desktop = window.matchMedia ? window.matchMedia('(min-width: 1024px)') : null;

    function isOpen() {
        return button.getAttribute('aria-expanded') === 'true';
    }

    function setOpen(open) {
        button.setAttribute('aria-expanded', open ? 'true' : 'false');
        panel.classList.toggle('is-open', open);
    }

    setOpen(false);

    button.addEventListener('click', () => {
        setOpen(!isOpen());
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && isOpen()) {
            setOpen(false);
            button.focus();
        }
    });

    panel.addEventListener('click', event => {
        if (event.target.closest('a')) setOpen(false);
    });

    document.addEventListener('click', event => {
        if (isOpen() && !header.contains(event.target)) setOpen(false);
    });

    if (desktop) {
        const onChange = event => {
            if (event.matches) setOpen(false);
        };
        if (desktop.addEventListener) desktop.addEventListener('change', onChange);
        else if (desktop.addListener) desktop.addListener(onChange);
    }
})();
