import React, { useEffect, useState } from 'react';
import { packetaAPI } from '../../../services/api';
import api from '../../../services/api';

const PacketaImportPanel = ({ onImported }) => {
    const [status, setStatus] = useState(null);
    const [stores, setStores] = useState([]);
    const [prodejnaId, setProdejnaId] = useState('5');
    const [file, setFile] = useState(null);
    const [fetchDays, setFetchDays] = useState('7');
    const [fetching, setFetching] = useState(false);
    const [message, setMessage] = useState('');
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        packetaAPI.getStatus().then(setStatus).catch(() => {});
        api.get('/stores/').then((res) => {
            const list = res.data?.results || res.data || [];
            setStores(Array.isArray(list) ? list : []);
        }).catch(() => {});
    }, []);

    const handleFetch = async () => {
        setMessage('');
        setFetching(true);
        try {
            const result = await packetaAPI.fetchAll(Number(fetchDays) || 1);
            const ok = (result.branches || []).filter((b) => b.prodejna_id && !b.error).length;
            setMessage(`Staženo: ${ok} poboček.`);
            onImported?.();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Stažení selhalo');
        } finally {
            setFetching(false);
        }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!file) {
            setMessage('Vyberte CSV.');
            return;
        }
        setMessage('');
        try {
            const result = await packetaAPI.importCsv(file, Number(prodejnaId));
            setMessage(`Import: ${result.created} nových, ${result.skipped} přeskočeno.`);
            onImported?.();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Import selhal');
        }
    };

    return (
        <section className="zk-panel zk-panel--import">
            <button
                type="button"
                className="zk-import-toggle"
                onClick={() => setExpanded((v) => !v)}
            >
                {expanded ? '▾' : '▸'} Import dat z Packety
            </button>
            {expanded && (
                <div className="zk-import-body">
                    {status?.fetch_available && (
                        <div className="zk-import-row">
                            <select value={fetchDays} onChange={(e) => setFetchDays(e.target.value)}>
                                <option value="1">1 den</option>
                                <option value="7">7 dní</option>
                                <option value="14">14 dní</option>
                            </select>
                            <button type="button" disabled={fetching} onClick={handleFetch}>
                                {fetching ? 'Stahuji…' : 'Stáhnout všechny pobočky'}
                            </button>
                        </div>
                    )}
                    <form className="zk-import-row" onSubmit={handleUpload}>
                        <select value={prodejnaId} onChange={(e) => setProdejnaId(e.target.value)}>
                            {(stores.length ? stores : [1, 2, 3, 4, 5, 6].map((id) => ({ id, nazev: id }))).map((s) => (
                                <option key={s.id} value={s.id}>{s.nazev || s.id}</option>
                            ))}
                        </select>
                        <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
                        <button type="submit">CSV import</button>
                    </form>
                    {message && <p className="zk-import-msg">{message}</p>}
                </div>
            )}
        </section>
    );
};

export default PacketaImportPanel;
