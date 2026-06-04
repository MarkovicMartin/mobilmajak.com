import React from 'react';

const fmtPct = (v) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v}%`);

const BenchmarkBadge = ({ benchmark, metricLabel = 'Položky' }) => {
    if (!benchmark || benchmark.poradi == null) return null;
    return (
        <div className="coaching-benchmark">
            <span className="coaching-benchmark-rank">#{benchmark.poradi}/{benchmark.pocet_prodejcu}</span>
            <span className="coaching-benchmark-vs">
                {metricLabel}: {fmtPct(benchmark.vs_prumer_pct)} vs průměr
            </span>
            <span className="coaching-benchmark-vs coaching-benchmark-vs--top">
                {fmtPct(benchmark.vs_top_pct)} vs top
            </span>
        </div>
    );
};

export default BenchmarkBadge;
