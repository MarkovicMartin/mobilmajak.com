import { useState, useEffect, useCallback } from 'react';
import { taskAPI } from '../services/api';

export function useTasks({ autoLoad = true, stav = 'vse', onLoaded } = {}) {
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(false);

    const load = useCallback(async (nextStav = stav) => {
        setLoading(true);
        try {
            const data = await taskAPI.list(nextStav);
            const list = Array.isArray(data) ? data : [];
            setTasks(list);
            onLoaded?.();
            return list;
        } catch {
            setTasks([]);
            return [];
        } finally {
            setLoading(false);
        }
    }, [stav, onLoaded]);

    const create = useCallback(async (payload, { prepend = false } = {}) => {
        const created = await taskAPI.create(payload);
        if (prepend) {
            setTasks((prev) => [created, ...prev]);
        } else {
            await load();
        }
        onLoaded?.();
        return created;
    }, [load, onLoaded]);

    const update = useCallback(async (id, payload, { merge = true } = {}) => {
        const updated = await taskAPI.update(id, payload);
        if (merge) {
            setTasks((list) => list.map((t) => (t.id === id ? updated : t)));
        } else {
            await load();
        }
        return updated;
    }, [load]);

    const markDone = useCallback((id) => update(id, { stav: 'hotovo' }), [update]);

    const toggleDone = useCallback(
        (task) => update(task.id, { stav: task.stav === 'hotovo' ? 'v_procesu' : 'hotovo' }),
        [update],
    );

    useEffect(() => {
        if (autoLoad) load();
    }, [autoLoad, load]);

    return {
        tasks,
        setTasks,
        loading,
        load,
        create,
        update,
        markDone,
        toggleDone,
    };
}
