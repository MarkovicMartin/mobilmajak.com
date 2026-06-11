/**
 * Čte design tokeny z CSS proměnných pro Recharts a vlastní SVG grafy.
 */

const CHART_COLOR_VARS = ['--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5'];

const FALLBACKS = {
    '--chart-1': '#1b2848',
    '--chart-2': '#e40b4d',
    '--chart-3': '#4a6fa5',
    '--chart-4': '#7b8fb8',
    '--chart-5': '#c9d4e8',
    '--text-primary': '#1b2848',
    '--text-muted': '#7b8fb8',
    '--text-secondary': '#4a5d7a',
    '--border-primary': '#d4dce8',
    '--border-secondary': '#e8edf5',
    '--bg-card': '#ffffff',
    '--accent-positive': '#15803d',
    '--accent-warning': '#b45309',
};

function readCssVar(name) {
    if (typeof document === 'undefined') {
        return FALLBACKS[name] || '';
    }
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || FALLBACKS[name] || '';
}

/** @returns {string[]} paleta pro série grafu */
export function getChartColors(count = 5) {
    const palette = CHART_COLOR_VARS.map((v) => readCssVar(v));
    if (count <= palette.length) {
        return palette.slice(0, count);
    }
    const out = [...palette];
    while (out.length < count) {
        out.push(palette[out.length % palette.length]);
    }
    return out;
}

/** Konfigurace pro Recharts (grid, osy, tooltip). */
export function getChartTheme() {
    return {
        colors: getChartColors(),
        grid: readCssVar('--border-secondary'),
        axis: readCssVar('--border-primary'),
        tick: readCssVar('--text-muted'),
        label: readCssVar('--text-primary'),
        tooltip: {
            background: readCssVar('--bg-card'),
            border: readCssVar('--border-primary'),
            color: readCssVar('--text-primary'),
        },
        positive: readCssVar('--accent-positive'),
        warning: readCssVar('--accent-warning'),
    };
}
