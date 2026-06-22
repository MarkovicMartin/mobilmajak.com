/** Varianta panduláčka pro úkol: hotovo | neutral | activity */

export function taskStatusIconVariant(task) {
    if (!task) return 'neutral';
    if (task.stav === 'hotovo') return 'hotovo';
    if (task.stav === 'blokovany' || task.stav === 'ceka_schvaleni') return 'activity';
    if (task.stav === 'novy' || task.is_unread) return 'activity';
    if ((task.komentare_count || 0) > 0) return 'activity';
    return 'neutral';
}

export const TASK_STATUS_ICON_LABELS = {
    hotovo: 'Hotovo',
    neutral: 'V procesu',
    activity: 'Nový úkol nebo aktivita',
};
