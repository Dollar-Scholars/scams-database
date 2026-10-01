/* Dashboard charts (scams/templates/scams/dashboard.html).
 *
 * Reads the chart data the view hands over with json_script, draws two Chart.js 4
 * column charts (monthly counts, often sparse, so bars rather than lines), and takes
 * every colour from the theme's CSS custom properties so the charts
 * follow the Dollar Scholars light/dark theme. They are recoloured whenever
 * theme-toggle.js fires 'ds:themechange'.
 *
 * Without Chart.js (CDN blocked or offline) the canvases are hidden and the
 * "Show the numbers" tables are opened instead.
 *
 * This file has no text of its own: the dataset labels, month labels and tooltips come
 * translated in the json_script payload, and numbers are formatted for the page
 * language (<html lang>) with Intl.NumberFormat.
 */
(() => {
    'use strict';

    const dataEl = document.getElementById('dashboard-chart-data');
    if (!dataEl) return;

    let payload;
    try {
        payload = JSON.parse(dataEl.textContent);
    } catch (_) {
        return;
    }

    const showTables = () => {
        document.querySelectorAll('.dash-chart').forEach((box) => { box.hidden = true; });
        document.querySelectorAll('details.chart-data').forEach((details) => { details.open = true; });
    };

    // Printing a canvas is unreliable; print the data tables instead.
    window.addEventListener('beforeprint', () => {
        document.querySelectorAll('details.chart-data').forEach((details) => { details.open = true; });
    });

    if (typeof window.Chart !== 'function') {
        showTables();
        return;
    }

    const Chart = window.Chart;
    const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

    const readTheme = () => ({
        series: css('--chart-1') || '#0f766e',
        grid: css('--chart-grid') || '#eaecf0',
        text: css('--chart-text') || '#475467',
        ink: css('--ink') || '#101828',
        surface: css('--ds-surface') || '#ffffff',
        line: css('--line') || '#eaecf0',
        font: css('--font-sans'),
    });

    // The page language, e.g. "es" or "zh-hans", if the browser can format numbers in it.
    const pageLocale = (() => {
        const lang = (document.documentElement.lang || '').trim();
        if (!lang || typeof Intl === 'undefined' || !Intl.NumberFormat) return undefined;
        try {
            return Intl.NumberFormat.supportedLocalesOf([lang]).length ? lang : undefined;
        } catch (_) {
            return undefined; // not a valid language tag
        }
    })();

    const formatNumber = (n) => {
        try {
            return new Intl.NumberFormat(pageLocale).format(n);
        } catch (_) {
            return String(n);
        }
    };

    // Tooltip text for one bar: the translated template from the server ("{count} reports")
    // with the number filled in, or just the number if there is no template.
    const tooltipText = (series, index, n) => {
        const template = series && Array.isArray(series.tooltips) ? series.tooltips[index] : null;
        const number = formatNumber(n);
        return typeof template === 'string' ? template.split('{count}').join(number) : number;
    };

    // Options are rebuilt from the current theme on every theme change.
    const buildOptions = (t, series) => ({
        responsive: true,
        locale: pageLocale, // axis numbers in the page language
        maintainAspectRatio: false,
        animation: reduceMotion ? false : { duration: 400 },
        interaction: { mode: 'index', intersect: false },
        layout: { padding: { top: 8, right: 4 } },
        plugins: {
            legend: { display: false, labels: { color: t.text } }, // one series: the card title names it
            tooltip: {
                backgroundColor: t.surface,
                titleColor: t.ink,
                bodyColor: t.ink,
                borderColor: t.line,
                borderWidth: 1,
                cornerRadius: 8,
                padding: 10,
                displayColors: false,
                titleFont: { weight: '700' },
                callbacks: { label: (ctx) => tooltipText(series, ctx.dataIndex, ctx.parsed.y) },
            },
        },
        scales: {
            x: {
                grid: { display: false },
                border: { color: t.grid },
                ticks: { color: t.text, maxRotation: 0, autoSkip: true, autoSkipPadding: 16 },
            },
            y: {
                beginAtZero: true,
                grid: { color: t.grid, lineWidth: 1 },
                border: { display: false },
                ticks: { color: t.text, precision: 0, padding: 8 },
            },
        },
    });

    const styleDataset = (dataset, t) => Object.assign(dataset, {
        backgroundColor: t.series,
        hoverBackgroundColor: t.series,
        borderRadius: 4,
        borderSkipped: 'start', // rounded data end, square at the baseline
        maxBarThickness: 24,
    });

    const charts = [];

    const draw = (canvasId, series) => {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !series || !Array.isArray(series.labels) || series.labels.length === 0) return;
        const t = readTheme();
        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: series.labels,
                datasets: [styleDataset({ label: series.label || '', data: series.data }, t)],
            },
            options: buildOptions(t, series),
        });
        chart.$series = series;
        charts.push(chart);
    };

    const applyTheme = () => {
        const t = readTheme();
        if (t.font) Chart.defaults.font.family = t.font;
        Chart.defaults.color = t.text;
        charts.forEach((chart) => {
            styleDataset(chart.data.datasets[0], t);
            chart.options = buildOptions(t, chart.$series);
            chart.update('none');
        });
    };

    const t0 = readTheme();
    if (t0.font) Chart.defaults.font.family = t0.font;
    Chart.defaults.color = t0.text;

    try {
        draw('scamChart', payload.submitted);
        draw('scamChart_o', payload.occurred);
    } catch (err) {
        showTables();
        if (window.console) console.error(err);
        return;
    }

    document.addEventListener('ds:themechange', applyTheme);
})();
