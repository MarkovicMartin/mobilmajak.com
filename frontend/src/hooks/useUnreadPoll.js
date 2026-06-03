import { useState, useEffect, useRef, useCallback } from 'react';

const DEFAULT_POLL_MS = 90000;

/**
 * Periodicky načítá počet nepřečtených položek a při nárůstu zobrazí toast.
 */
export function useUnreadPoll({ enabled, fetchCount, onNotify, pollMs = DEFAULT_POLL_MS }) {
    const [count, setCount] = useState(0);
    const prevRef = useRef(0);
    const initialRef = useRef(true);

    const refresh = useCallback(async () => {
        if (!enabled) {
            setCount(0);
            return;
        }
        try {
            const n = await fetchCount();
            const next = typeof n === 'number' ? n : 0;
            if (!initialRef.current && next > prevRef.current && onNotify) {
                onNotify(next - prevRef.current, next);
            }
            initialRef.current = false;
            prevRef.current = next;
            setCount(next);
        } catch {
            setCount(0);
        }
    }, [enabled, fetchCount, onNotify]);

    useEffect(() => {
        initialRef.current = true;
        prevRef.current = 0;
    }, [enabled]);

    useEffect(() => {
        refresh();
    }, [refresh]);

    useEffect(() => {
        if (!enabled) return undefined;
        const id = window.setInterval(refresh, pollMs);
        const onFocus = () => refresh();
        const onVis = () => {
            if (document.visibilityState === 'visible') refresh();
        };
        window.addEventListener('focus', onFocus);
        document.addEventListener('visibilitychange', onVis);
        return () => {
            clearInterval(id);
            window.removeEventListener('focus', onFocus);
            document.removeEventListener('visibilitychange', onVis);
        };
    }, [enabled, refresh, pollMs]);

    return { count, refresh };
}
