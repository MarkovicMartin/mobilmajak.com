import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { coachingAPI } from '../../services/api';
import { PageHeader } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import SellerCompare from '../coaching/sections/SellerCompare';
import '../coaching/CoachingModule.css';
import '../coaching/CoachingNav.css';

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

const sellerName = (user) => (
    user ? `${user.jmeno || ''} ${user.prijmeni || ''}`.trim() : ''
);

const VykonModule = () => {
    const { user } = useAuth();
    const [mesic, setMesic] = useState(monthKey(new Date()));
    const [staffUsers, setStaffUsers] = useState([]);
    const monthOptions = useMemo(() => buildMonthOptions(), []);

    const loadFilters = useCallback(async () => {
        const res = await coachingAPI.getFilters();
        if (res.success) {
            setStaffUsers(res.prodejci || []);
        }
    }, []);

    useEffect(() => { loadFilters(); }, [loadFilters]);

    return (
        <div className="coaching-module">
            <PageHeader title="Porovnání výkonu" />
            <div className="coaching-content">
                <SellerCompare
                    staffUsers={staffUsers}
                    mesic={mesic}
                    monthOptions={monthOptions}
                    onMesicChange={setMesic}
                    lockedPrimaryId={user?.id || ''}
                    lockedPrimaryName={sellerName(user)}
                    userSafe
                />
            </div>
        </div>
    );
};

export default VykonModule;
