import { useState, useEffect, useCallback, useRef } from 'react';
import { getApiEndpoints } from '../config/apiConfig';

const CACHE_TTL_MS = 90_000;
const metricsCache = new Map();

function cacheKey(userId, date) {
    return `${userId}|${date || ''}`;
}

function readCache(key) {
    const entry = metricsCache.get(key);
    if (!entry || Date.now() - entry.at > CACHE_TTL_MS) return null;
    return entry;
}

function writeCache(key, payload) {
    metricsCache.set(key, { ...payload, at: Date.now() });
}

/**
 * Načte denní/měsíční metriky a body prodejce (dashboard + profil).
 * Krátkodobá cache sdílená mezi dashboardem a profilem (90 s).
 */
export function useSalespersonMetrics(userId, { date = '', enabled = true } = {}) {
    const key = enabled && userId ? cacheKey(userId, date) : null;
    const cached = key ? readCache(key) : null;

    const [today, setToday] = useState(cached?.today ?? null);
    const [month, setMonth] = useState(cached?.month ?? null);
    const [todayPoints, setTodayPoints] = useState(cached?.todayPoints ?? null);
    const [monthPoints, setMonthPoints] = useState(cached?.monthPoints ?? null);
    const [loading, setLoading] = useState(enabled && !!userId && !cached);
    const [error, setError] = useState('');
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;
        return () => { mountedRef.current = false; };
    }, []);

    const applyPayload = useCallback((payload) => {
        setToday(payload.today);
        setMonth(payload.month);
        setTodayPoints(payload.todayPoints);
        setMonthPoints(payload.monthPoints);
    }, []);

    const refresh = useCallback(async ({ background = false } = {}) => {
        if (!enabled || !userId) {
            setToday(null);
            setMonth(null);
            setTodayPoints(null);
            setMonthPoints(null);
            setLoading(false);
            return;
        }

        const k = cacheKey(userId, date);
        if (!background) setLoading(true);
        setError('');

        try {
            const endpoints = getApiEndpoints();
            const dateQuery = date ? `&date=${date}` : '';
            const base = `user_id=${userId}${dateQuery}`;
            const [dailyRes, monthlyRes, dailyPtsRes, monthlyPtsRes] = await Promise.all([
                fetch(`${endpoints.salespersonToday}?${base}`, { credentials: 'include' }),
                fetch(`${endpoints.salespersonMonthly}?${base}`, { credentials: 'include' }),
                fetch(`${endpoints.salespersonPointsToday}?${base}`, { credentials: 'include' }),
                fetch(`${endpoints.salespersonPointsMonthly}?${base}`, { credentials: 'include' }),
            ]);

            if (!mountedRef.current) return;

            const payload = {
                today: null,
                month: null,
                todayPoints: null,
                monthPoints: null,
            };

            if (dailyRes.ok) payload.today = await dailyRes.json();
            else setError('Chyba při načítání denních dat');

            if (monthlyRes.ok) payload.month = await monthlyRes.json();
            else setError('Chyba při načítání měsíčních dat');

            if (dailyPtsRes.ok) payload.todayPoints = await dailyPtsRes.json();
            if (monthlyPtsRes.ok) payload.monthPoints = await monthlyPtsRes.json();

            applyPayload(payload);
            writeCache(k, payload);
        } catch {
            if (mountedRef.current) setError('Chyba při komunikaci se serverem');
        } finally {
            if (mountedRef.current) setLoading(false);
        }
    }, [userId, date, enabled, applyPayload]);

    useEffect(() => {
        if (!enabled || !userId) return undefined;

        const k = cacheKey(userId, date);
        const hit = readCache(k);
        if (hit) {
            applyPayload(hit);
            setLoading(false);
            refresh({ background: true });
            return undefined;
        }

        refresh();
        return undefined;
    }, [userId, date, enabled, applyPayload, refresh]);

    return { today, month, todayPoints, monthPoints, loading, error, refresh };
};
