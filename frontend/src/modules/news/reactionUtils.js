export const REACTION_EMOJI = {
    like: '👍',
    srdce: '❤️',
    smich: '😂',
    prekvapeni: '😮',
};

export const REACTION_ORDER = ['like', 'srdce', 'smich', 'prekvapeni'];

export const reactionUserName = (reaction) => {
    const u = reaction?.uzivatel;
    if (!u) return 'Neznámý';
    return `${u.jmeno || ''} ${u.prijmeni || ''}`.trim() || u.uzivatelske_jmeno || 'Neznámý';
};

export const reactionsByType = (reakce, type) =>
    (reakce || []).filter((r) => r.typ === type);

export const reactionNamesForType = (reakce, type) =>
    reactionsByType(reakce, type).map(reactionUserName);

export const reactionSummaryLines = (reakce) =>
    REACTION_ORDER
        .map((type) => {
            const names = reactionNamesForType(reakce, type);
            if (!names.length) return null;
            return `${REACTION_EMOJI[type]} ${names.join(', ')}`;
        })
        .filter(Boolean);
