import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { coachingAPI } from '../../services/api';
import CoachingNav from './CoachingNav';
import TeamRoster from './sections/TeamRoster';
import SellerProfile from './sections/SellerProfile';
import SellerCompare from './sections/SellerCompare';
import './CoachingModule.css';

const monthKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;

const buildMonthOptions = (count = 18) => {
    const out = [];
    const d = new Date();
    for (let i = 0; i < count; i += 1) {
        const y = d.getFullYear();
        const m = d.getMonth() + 1;
        out.push({
            value: `${y}-${String(m).padStart(2, '0')}`,
            label: d.toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' }),
        });
        d.setMonth(d.getMonth() - 1);
    }
    return out;
};

const CoachingModule = () => {
    const location = useLocation();
    const [mesic, setMesic] = useState(monthKey(new Date()));
    const [prodejnaId, setProdejnaId] = useState('');
    const [prodejci, setProdejci] = useState([]);
    const [prodejny, setProdejny] = useState([]);
    const [staffUsers, setStaffUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [rosterError, setRosterError] = useState('');

    const monthOptions = useMemo(() => buildMonthOptions(), []);
    const isSellerDetail = location.pathname.includes('/seller/');

    const loadFilters = useCallback(async () => {
        const res = await coachingAPI.getFilters();
        if (res.success) {
            setProdejny(res.prodejny || []);
            setStaffUsers(res.prodejci || []);
            if ((res.prodejny || []).length === 1) {
                setProdejnaId(String(res.prodejny[0].id));
            }
        }
    }, []);

    const loadRoster = useCallback(async () => {
        setLoading(true);
        setRosterError('');
        try {
            const [rok, m] = mesic.split('-').map(Number);
            const params = { mesic, rok, mesic_cislo: m };
            if (prodejnaId) params.prodejna_id = prodejnaId;
            const res = await coachingAPI.getRoster(params);
            if (res.success) {
                setProdejci(res.prodejci || []);
            } else {
                setProdejci([]);
                setRosterError(res.error || 'Nepodařilo se načíst přehled týmu');
            }
        } catch {
            setProdejci([]);
            setRosterError('Chyba při načítání přehledu týmu');
        } finally {
            setLoading(false);
        }
    }, [mesic, prodejnaId]);

    useEffect(() => { loadFilters(); }, [loadFilters]);
    useEffect(() => {
        if (!isSellerDetail) loadRoster();
    }, [loadRoster, isSellerDetail]);

    return (
        <div className="coaching-module">
            <CoachingNav
                monthValue={mesic}
                monthOptions={monthOptions}
                onMonthChange={setMesic}
                prodejnaId={prodejnaId}
                prodejny={prodejny}
                onProdejnaChange={setProdejnaId}
            />
            <div className="coaching-content">
                <Routes>
                    <Route
                        path=""
                        element={(
                            <TeamRoster
                                prodejci={prodejci}
                                loading={loading}
                                mesic={mesic}
                                error={rosterError}
                            />
                        )}
                    />
                    <Route
                        path="compare"
                        element={<SellerCompare staffUsers={staffUsers} mesic={mesic} />}
                    />
                    <Route
                        path="seller/:userId"
                        element={(
                            <SellerProfile
                                staffUsers={staffUsers}
                                mesic={mesic}
                                onMesicChange={setMesic}
                            />
                        )}
                    />
                </Routes>
            </div>
        </div>
    );
};

export default CoachingModule;
