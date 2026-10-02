/* Scam awareness page (templates/scams/scam_awareness_page.html).
 *
 * - Topic accordion: one topic open at a time. Opening a topic marks it "Reviewed" and
 *   moves the progress bar.
 * - Warning-signs checklist: ticked signs are highlighted.
 * Both are remembered in localStorage under the same keys the page has always used, so
 * returning visitors keep their progress.
 *
 * This file holds no user-visible text. Translated strings come from the page's
 * <script type="application/json" id="awareness-i18n"> block, rendered by Django i18n.
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'scamAwarenessProgress_v1';
    var CHECKLIST_KEY = 'scamAwarenessChecklist_v1';

    var root = document.querySelector('.awareness-page');
    if (!root) return;

    function safeGet(key) {
        try { return JSON.parse(window.localStorage.getItem(key)) || {}; }
        catch (e) { return {}; }
    }

    function safeSet(key, value) {
        try { window.localStorage.setItem(key, JSON.stringify(value)); }
        catch (e) { /* ignore storage issues (private mode, blocked storage) */ }
    }

    /* Translated strings rendered by the template. Values may contain HTML entities
     * (translations are HTML), so decode them to plain text before using textContent. */
    function decodeHtml(text) {
        try { return new DOMParser().parseFromString(text, 'text/html').documentElement.textContent; }
        catch (e) { return text; }
    }

    var messages = {};
    var messagesEl = document.getElementById('awareness-i18n');
    if (messagesEl) {
        try { messages = JSON.parse(messagesEl.textContent) || {}; }
        catch (e) { messages = {}; }
    }

    function progressText(reviewedCount, total) {
        // messages.progress is e.g. "Topics reviewed: {reviewed} of 4" in the page language
        if (typeof messages.progress === 'string' && messages.progress.indexOf('{reviewed}') !== -1) {
            return decodeHtml(messages.progress.split('{reviewed}').join(String(reviewedCount)));
        }
        return reviewedCount + ' / ' + total;  // language-neutral fallback
    }

    var progress = safeGet(STORAGE_KEY);
    var checklist = safeGet(CHECKLIST_KEY);

    /* ---- Topics and progress ---- */
    var accordionItems = root.querySelectorAll('[data-accordion-item]');
    var progressBox = root.querySelector('.awareness-progress');
    var progressBar = root.querySelector('[data-progress]');
    var progressFill = root.querySelector('[data-progress-fill]');
    var progressLabel = root.querySelector('[data-progress-label]');
    var totalTopics = accordionItems.length;

    function updateProgress() {
        // Count only topics on the page, so ids stored by older versions are ignored
        var reviewedCount = 0;
        accordionItems.forEach(function (item) {
            if (progress[item.getAttribute('data-item-id')]) reviewedCount += 1;
        });
        var percent = totalTopics ? Math.round((reviewedCount / totalTopics) * 100) : 0;
        var text = progressText(reviewedCount, totalTopics);

        if (progressFill) progressFill.style.width = percent + '%';
        if (progressLabel && progressLabel.textContent !== text) progressLabel.textContent = text;
        if (progressBar) {
            progressBar.setAttribute('aria-valuemax', String(totalTopics));
            progressBar.setAttribute('aria-valuenow', String(reviewedCount));
            progressBar.setAttribute('aria-valuetext', text);
        }
        if (progressBox) progressBox.classList.toggle('is-complete', totalTopics > 0 && reviewedCount === totalTopics);
    }

    function setOpen(item, open) {
        item.classList.toggle('is-open', open);
        item.querySelector('[data-accordion-trigger]').setAttribute('aria-expanded', String(open));
        item.querySelector('[data-accordion-panel]').setAttribute('aria-hidden', String(!open));
    }

    accordionItems.forEach(function (item) {
        var trigger = item.querySelector('[data-accordion-trigger]');
        var panel = item.querySelector('[data-accordion-panel]');
        var id = item.getAttribute('data-item-id');
        if (!trigger || !panel) return;

        if (progress[id]) {
            item.classList.add('is-reviewed');
        }

        trigger.addEventListener('click', function () {
            var isOpen = item.classList.contains('is-open');
            var group = item.closest('[data-accordion-group]');

            if (group) {
                group.querySelectorAll('[data-accordion-item].is-open').forEach(function (openItem) {
                    if (openItem !== item) setOpen(openItem, false);
                });
            }

            setOpen(item, !isOpen);

            if (!isOpen && !progress[id]) {
                progress[id] = true;
                safeSet(STORAGE_KEY, progress);
                item.classList.add('is-reviewed');
                updateProgress();
            }
        });

        panel.setAttribute('aria-hidden', 'true');
    });

    updateProgress();

    /* ---- Warning-signs checklist ---- */
    var checkboxes = root.querySelectorAll('[data-checklist-item]');

    function markItem(box) {
        var item = box.closest('.warning-item');
        if (item) item.classList.toggle('is-checked', box.checked);
    }

    checkboxes.forEach(function (box) {
        var id = box.getAttribute('data-checklist-item');
        box.checked = !!checklist[id];
        markItem(box);

        box.addEventListener('change', function () {
            checklist[id] = box.checked;
            safeSet(CHECKLIST_KEY, checklist);
            markItem(box);
        });
    });

    var resetButton = root.querySelector('[data-reset-checklist]');
    if (resetButton) {
        resetButton.addEventListener('click', function () {
            checkboxes.forEach(function (input) {
                input.checked = false;
                markItem(input);
            });
            checklist = {};
            safeSet(CHECKLIST_KEY, checklist);
        });
    }
})();
