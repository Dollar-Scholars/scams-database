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

    const plural = (n) => `${n.toLocaleString()} ${n === 1 ? 'report' : 'reports'}`;

    // Options are rebuilt from the current theme on every theme change.
    const buildOptions = (t) => ({
        responsive: true,
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
                callbacks: { label: (ctx) => plural(ctx.parsed.y) },
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

    const draw = (canvasId, series, label) => {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !series || !Array.isArray(series.labels) || series.labels.length === 0) return;
        const t = readTheme();
        charts.push(new Chart(canvas, {
            type: 'bar',
            data: { labels: series.labels, datasets: [styleDataset({ label, data: series.data }, t)] },
            options: buildOptions(t),
        }));
    };

    const applyTheme = () => {
        const t = readTheme();
        if (t.font) Chart.defaults.font.family = t.font;
        Chart.defaults.color = t.text;
        charts.forEach((chart) => {
            styleDataset(chart.data.datasets[0], t);
            chart.options = buildOptions(t);
            chart.update('none');
        });
    };

    const t0 = readTheme();
    if (t0.font) Chart.defaults.font.family = t0.font;
    Chart.defaults.color = t0.text;

    try {
        draw('scamChart', payload.submitted, 'Reports submitted');
        draw('scamChart_o', payload.occurred, 'Scams that occurred');
    } catch (err) {
        showTables();
        if (window.console) console.error(err);
        return;
    }

    document.addEventListener('ds:themechange', applyTheme);
})();
