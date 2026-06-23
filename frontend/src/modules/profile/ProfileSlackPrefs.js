import React, { useEffect, useMemo, useState } from 'react';

const SLACK_MINE_GROUPS = [
    {
        title: 'Moje úkoly',
        items: [
            { key: 'assigned_mine', label: 'Nový úkol mi přiřazen' },
            { key: 'created_confirm', label: 'Potvrzení úkolu, který založím' },
            { key: 'due_soon_mine', label: 'Blížící se termín (jsem řešitel nebo zadavatel)' },
            { key: 'overdue_mine', label: 'Po termínu (jsem řešitel nebo zadavatel)' },
            { key: 'awaiting_approval', label: 'Čeká na mé schválení' },
            { key: 'completed_mine', label: 'Dokončení úkolu, který jsem zadal' },
        ],
    },
];

const SLACK_ADMIN_GROUPS = [
    {
        title: 'Všechny úkoly ve firmě',
        subtitle: 'Pro dohled nad plněním – dostanete zprávu i k cizím úkolům.',
        items: [
            { key: 'created_all', label: 'Každý nový přiřazený úkol' },
            { key: 'due_soon_all', label: 'Blížící se termín (všechny úkoly)' },
            { key: 'overdue_all', label: 'Po termínu (všechny úkoly)' },
        ],
    },
    {
        title: 'Komentáře',
        subtitle: 'Řešitelé komentáře od ostatních dostávají vždy – bez možnosti vypnout.',
        items: [
            { key: 'comment_mine', label: 'Komentář u úkolů, kde jsem zadavatel / vedoucí' },
            { key: 'comment_all', label: 'Každý nový komentář u libovolného úkolu' },
        ],
    },
];

const buildDefaultPrefs = (groups) => groups.flatMap((g) => g.items).reduce((acc, item) => {
    acc[item.key] = !item.key.endsWith('_all');
    return acc;
}, {});

const ProfileSlackPrefs = ({ user, onSaved }) => {
    const isAdmin = user?.role === 'ADMIN';
    const groups = useMemo(
        () => (isAdmin ? [...SLACK_MINE_GROUPS, ...SLACK_ADMIN_GROUPS] : SLACK_MINE_GROUPS),
        [isAdmin],
    );
    const defaultPrefs = useMemo(() => buildDefaultPrefs(groups), [groups]);

    const [prefs, setPrefs] = useState({ ...defaultPrefs });
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState('');

    useEffect(() => {
        if (user?.slack_ukoly_prefs) {
            setPrefs({ ...defaultPrefs, ...user.slack_ukoly_prefs });
        }
    }, [user, defaultPrefs]);

    const toggle = (key) => {
        setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
    };

    const handleSave = async () => {
        setLoading(true);
        setMessage('');
        try {
            const response = await fetch('/api/users/profile/update/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ slack_ukoly_prefs: prefs }),
            });
            if (response.ok) {
                const updated = await response.json();
                setPrefs({ ...defaultPrefs, ...updated.slack_ukoly_prefs });
                onSaved?.(updated);
                setMessage('Nastavení Slack notifikací uloženo');
                setMessageType('success');
            } else {
                const err = await response.json();
                setMessage(err.error || 'Uložení se nezdařilo');
                setMessageType('error');
            }
        } catch {
            setMessage('Chyba při komunikaci se serverem');
            setMessageType('error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="info-section slack-prefs-section">
            <h3>Slack – úkoly</h3>
            <p className="slack-prefs-hint">
                Upozornění chodí do Slacku (DM od bota). E-mail v profilu musí sedět se Slack účtem.
                {' '}
                Jste-li přiřazeni k úkolu, komentáře od ostatních vám chodí vždy.
            </p>
            {message && <div className={`message ${messageType}`}>{message}</div>}
            {groups.map((group) => (
                <div key={group.title} className="slack-prefs-group">
                    <h4>{group.title}</h4>
                    {group.subtitle && <p className="slack-prefs-subtitle">{group.subtitle}</p>}
                    <ul className="slack-prefs-list">
                        {group.items.map((item) => (
                            <li key={item.key}>
                                <label className="slack-pref-label">
                                    <input
                                        type="checkbox"
                                        checked={!!prefs[item.key]}
                                        onChange={() => toggle(item.key)}
                                    />
                                    <span>{item.label}</span>
                                </label>
                            </li>
                        ))}
                    </ul>
                </div>
            ))}
            <button
                type="button"
                className="save-button slack-prefs-save"
                onClick={handleSave}
                disabled={loading}
            >
                {loading ? 'Ukládám…' : 'Uložit notifikace'}
            </button>
        </div>
    );
};

export default ProfileSlackPrefs;
