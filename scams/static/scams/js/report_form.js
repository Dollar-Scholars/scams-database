/* Report a scam page (scams/report_form.html).
   - Severity slider: live label, filled track and colour band (low / medium / high).
     updateSeverity() stays global: the widget calls it from oninput (see forms.py).
   - Date it happened: no future dates (max = today).
   - Submit anonymously: switches off and clears the name and phone fields. The email
     stays on: it is required so the team can follow up, and is never shown publicly.
   - Error summary: focused on load; its links focus the field they point to.
   - Words shown on the page come from the template (#report-form-i18n), translated. */
(function () {
    'use strict';

    // The page's words, in the page's language: report_form.html renders them as JSON in
    // <script type="application/json" id="report-form-i18n">. Nothing here is in English, so
    // if that block is missing the slider just shows its number.
    function readStrings() {
        var el = document.getElementById('report-form-i18n');
        if (!el) return {};
        try {
            return JSON.parse(el.textContent) || {};
        } catch (e) {
            return {};
        }
    }

    // { "1": <word for 1>, ..., "5": <word for 5> }: the same words as the scale under the slider.
    // Read on first use, so it works wherever the script tag is.
    var severityLabels = null;

    function severityLabel(value) {
        if (!severityLabels) severityLabels = readStrings().severityLabels || {};
        return severityLabels[value] || '';
    }

    // Same colour bands as before the redesign: 1-2 low (green), 3 medium (amber), 4-5 high (red)
    function severityLevel(value) {
        if (value <= 2) return 'low';
        if (value === 3) return 'medium';
        return 'high';
    }

    function updateSeverity(val) {
        var range = document.getElementById('sevRange');
        if (!range) return;

        var min = Number(range.min) || 1;
        var max = Number(range.max) || 5;
        var value = Math.round(Number(val));
        if (!isFinite(value)) value = min;
        value = Math.min(max, Math.max(min, value));

        var percent = ((value - min) / (max - min)) * 100;
        var level = severityLevel(value);
        var label = severityLabel(value);
        var text = label ? value + ' · ' + label : String(value);

        range.style.setProperty('--fill', percent + '%');
        range.setAttribute('data-level', level);
        range.setAttribute('aria-valuetext', text);

        var output = document.getElementById('sevValue');
        if (output) {
            output.textContent = text;
            output.setAttribute('data-level', level);
        }
    }

    window.updateSeverity = updateSeverity;

    function localToday() {
        var now = new Date();
        return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().split('T')[0];
    }

    function init() {
        // 1. Severity
        var severityInput = document.querySelector('[name="severity"]');
        if (severityInput) {
            updateSeverity(severityInput.value || 1);
            severityInput.addEventListener('change', function () {
                updateSeverity(this.value);
            });
        }

        // 2. No future dates
        var dateField = document.querySelector('input[type="date"]');
        if (dateField) {
            dateField.setAttribute('max', localToday());
        }

        // 3. Anonymous: grey out name and phone (never the required email).
        //    A field with an error stays on, so the error summary never links to a disabled control.
        var anonCheckbox = document.querySelector('[name="anonymous"]');
        var fieldsToGrey = ['reporter_name', 'reporter_phone'];

        function handleAnonymousStatus() {
            var isChecked = anonCheckbox.checked;

            fieldsToGrey.forEach(function (fieldName) {
                var input = document.querySelector('[name="' + fieldName + '"]');
                if (!input || input.getAttribute('aria-invalid') === 'true') return;
                var container = input.closest('.field');

                if (isChecked) {
                    input.disabled = true;
                    input.value = '';
                    if (container) container.classList.add('is-greyed-out');
                } else {
                    input.disabled = false;
                    if (container) container.classList.remove('is-greyed-out');
                }
            });
        }

        if (anonCheckbox) {
            anonCheckbox.addEventListener('change', handleAnonymousStatus);
            handleAnonymousStatus();
        }

        // 4. Error summary
        var summary = document.getElementById('error-summary');
        if (summary) {
            summary.focus();
            summary.addEventListener('click', function (event) {
                var link = event.target.closest('a[href^="#"]');
                if (!link) return;
                var target = document.getElementById(link.getAttribute('href').slice(1));
                if (!target) return;
                event.preventDefault();
                // Scroll the field's label (or legend) into view, then focus the control
                var field = target.closest('.field');
                var heading = field && field.querySelector('legend, label');
                (heading || target).scrollIntoView({ block: 'start' });
                target.focus({ preventScroll: true });
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
