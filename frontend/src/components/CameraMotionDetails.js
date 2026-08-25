import React from 'react';
import CameraBeacon from './CameraBeacon';
import {
    formatPragueDay,
    formatPragueEventAt,
    formatPragueHm,
    pragueDateKey,
} from '../utils/pragueDateTime';
import './CameraMotionDetails.css';

function motionToCamera(motion) {
    if (!motion?.in_pilot) return null;
    return {
        in_pilot: true,
        active: motion.status === 'active',
    };
}

function formatDuration(minutes) {
    const m = Number(minutes) || 0;
    if (m < 60) return `${m} min`;
    const h = Math.floor(m / 60);
    const r = m % 60;
    return r > 0 ? `${h} h ${r} min` : `${h} h`;
}

function formatQuietRange(from, to, ongoing) {
    const start = formatPragueHm(from);
    if (ongoing) return `${start} → teď`;
    if (!to) return start;
    if (pragueDateKey(from) === pragueDateKey(to)) {
        return `${start} → ${formatPragueHm(to)}`;
    }
    return `${start} → ${formatPragueDay(to)} ${formatPragueHm(to)}`;
}

function groupQuietByDay(periods) {
    const groups = [];
    const byKey = new Map();
    periods.forEach((p) => {
        const key = pragueDateKey(p.from);
        if (!byKey.has(key)) {
            const group = { key, from: p.from, periods: [] };
            byKey.set(key, group);
            groups.push(group);
        }
        byKey.get(key).periods.push(p);
    });
    return groups;
}

/**
 * Majáček + volitelný rozbalovací log klidu (bez pohybu).
 * compact = jen majáček a štítek; detail v <details>.
 */
export default function CameraMotionDetails({
    motion,
    detail,
    compact = true,
    defaultOpen = false,
}) {
    if (!motion?.in_pilot) return null;

    const camera = motionToCamera(motion);
    const quietPeriods = detail?.quiet_periods || [];
    const currentQuiet = detail?.current_quiet_minutes ?? motion.quiet_minutes;
    const minQuiet = detail?.quiet_log_min_minutes || 10;
    const dayGroups = groupQuietByDay(quietPeriods);

    const beaconTitle = motion.last_event_at
        ? `Poslední signál: ${formatPragueEventAt(motion.last_event_at)}`
        : undefined;

    const summary = (
        <span className="camera-motion-summary" onClick={(e) => e.stopPropagation()}>
            <CameraBeacon camera={camera} title={beaconTitle} />
            <span className={`camera-motion-label camera-motion-label--${motion.status || 'unknown'}`}>
                {motion.label || (camera.active ? 'Pohyb' : 'Bez pohybu')}
            </span>
        </span>
    );

    if (compact) {
        return (
            <details
                className="camera-motion-details"
                open={defaultOpen}
                onClick={(e) => e.stopPropagation()}
            >
                <summary className="camera-motion-details-summary">{summary}</summary>
                <div className="camera-motion-details-body">
                    {currentQuiet != null && currentQuiet >= 5 && motion.status === 'quiet' && (
                        <p className="camera-motion-current-quiet">
                            Aktuálně bez pohybu: <strong>{formatDuration(currentQuiet)}</strong>
                        </p>
                    )}
                    {quietPeriods.length === 0 ? (
                        <p className="camera-motion-empty">
                            Žádné období bez pohybu ≥ {minQuiet} min.
                        </p>
                    ) : (
                        dayGroups.map((day) => (
                            <div key={day.key} className="camera-motion-day">
                                <div className="camera-motion-day-label">
                                    {formatPragueDay(day.from)}
                                </div>
                                <ul className="camera-motion-quiet-list">
                                    {day.periods.map((p) => (
                                        <li
                                            key={`${p.from}-${p.to || 'now'}`}
                                            className={p.minutes >= 60 ? 'camera-motion-quiet--long' : undefined}
                                        >
                                            <span className="camera-motion-quiet-range">
                                                {formatQuietRange(p.from, p.to, p.ongoing)}
                                            </span>
                                            <span className="camera-motion-quiet-dur">
                                                {formatDuration(p.minutes)}
                                                {p.ongoing ? ' (běží)' : ''}
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))
                    )}
                </div>
            </details>
        );
    }

    return summary;
}
