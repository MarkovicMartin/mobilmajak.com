/**
 * Připraví data z formuláře pro API (create / update).
 */
export function prepareUserSubmitData(formData, editingUser) {
    const submitData = { ...formData };

    delete submitData.id;

    if (submitData.prodejna) {
        const pid = parseInt(submitData.prodejna, 10);
        submitData.prodejna_id = !Number.isNaN(pid) ? pid : null;
    } else {
        submitData.prodejna_id = null;
    }
    delete submitData.prodejna;

    const technikId = parseInt(submitData.technik_id, 10);
    if (Number.isNaN(technikId) || technikId < 0) {
        return { error: 'Zadejte platné Technik ID (EDA/Pohoda) – celé číslo ≥ 0.' };
    }
    submitData.technik_id = technikId;

    if (editingUser) {
        if (submitData.heslo && submitData.heslo.trim()) {
            submitData.nove_heslo = submitData.heslo.trim();
        }
        delete submitData.heslo;
    } else if (!submitData.heslo || submitData.heslo.length < 6) {
        return { error: 'Heslo musí mít alespoň 6 znaků.' };
    }

    return { data: submitData };
}

const STAFF_ROLES = ['PRODEJCE', 'VEDOUCI'];

/**
 * Odhad dalšího systémového ID (jen řada prodejce/vedoucí, bez admin účtů).
 */
export function estimateNextUserId(users) {
    const all = users || [];
    const staff = all.filter((user) => STAFF_ROLES.includes(user.role));
    if (staff.length === 0) {
        return 1;
    }
    const occupied = new Set(all.map((user) => Number(user.id)).filter((id) => !Number.isNaN(id)));
    let candidate = staff.reduce((max, user) => Math.max(max, Number(user.id) || 0), 0) + 1;
    while (occupied.has(candidate)) {
        candidate += 1;
    }
    return candidate;
}

/**
 * Sestaví čitelnou chybovou zprávu z odpovědi API nebo axios chyby.
 */
export function formatUserApiError(payload) {
    if (!payload) {
        return null;
    }
    const message = payload.message || 'Chyba při ukládání uživatele';
    if (!payload.errors) {
        return message;
    }
    const details = Object.entries(payload.errors)
        .map(([field, errors]) => {
            const text = Array.isArray(errors) ? errors.join(', ') : String(errors);
            return `${field}: ${text}`;
        })
        .join('\n');
    return `${message}\n\n${details}`;
}
