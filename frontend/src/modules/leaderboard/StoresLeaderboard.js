import React, { useMemo } from 'react';
import PointsLeaderboard from './PointsLeaderboard';

/**
 * Žebříček prodejen – stejné UI jako bodový žebříček, data z API stores.
 */
const StoresLeaderboard = ({ data, loading, vicepraceLeader }) => {
    const pointsShape = useMemo(
        () => (data || []).map((row) => ({
            ...row,
            prodejce: row.prodejna,
            prodejna: row.stredisko || '',
            last_month_points: 0,
            last_shift_points: 0,
        })),
        [data],
    );

    const meta = vicepraceLeader
        ? {
            viceprace_leader: {
                ...vicepraceLeader,
                prodejce: vicepraceLeader.prodejce || vicepraceLeader.prodejna,
            },
        }
        : null;

    return (
        <PointsLeaderboard
            data={pointsShape}
            loading={loading}
            currentUser={null}
            period="month"
            vicepraceLeader={meta?.viceprace_leader}
            hideLastPeriodColumn
            tableTitle="🏪 Kompletní žebříček prodejen"
            sellerColumnLabel="Prodejna"
            hideStoreColumn
            emptyTitle="📊 Žádná data k zobrazení"
            emptyMessage="Pro aktuální měsíc nejsou k dispozici žádná data o prodejnách."
        />
    );
};

export default StoresLeaderboard;
