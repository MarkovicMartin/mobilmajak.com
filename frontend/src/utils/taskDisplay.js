/** Zobrazovaný název úkolu – vysledek s fallbackem na legacy ukol. */

export function taskDisplayTitle(task) {
    if (!task) return '';
    const title = (task.vysledek || task.ukol || '').trim();
    return title.split('\n')[0];
}

export function isPrirazenySop(task) {
    return task?.typ === 'prirazeny';
}

export const ACTIVE_TASK_STAVY = ['novy', 'v_procesu', 'blokovany'];

export function isActiveTask(task) {
    return task && ACTIVE_TASK_STAVY.includes(task.stav);
}

export const STAV_LABELS = {
    novy: 'Nový',
    v_procesu: 'V procesu',
    blokovany: 'Blokovaný',
    ceka_schvaleni: 'Čeká schválení',
    hotovo: 'Hotovo',
};
