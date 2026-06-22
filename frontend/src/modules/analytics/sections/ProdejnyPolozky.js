import React, { useCallback, useRef, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AnalyticsSectionWrapper from '../AnalyticsSectionWrapper';
import PolozkyMetricPicker, { DEFAULT_VISIBLE_METRICS } from '../components/PolozkyMetricPicker';
import ProdejnyPolozkyView from './ProdejnyPolozkyView';
import {
    shiftFiltersOneYearBack,
} from './celkovaPeriodUtils';
import {
    buildInitialPolozkyFilters,
    mergePolozkyScope,
    pickPolozkyScope,
} from './polozkyFilters';
import { storeAPI } from '../../../services/api';
import './CelkovaCisla.css';
import './Polozky.css';
import './ProdejnyPolozky.css';

const mesicFromFilters = (filters) => {
    if (filters?.period === 'monthly_select' && filters.selected_month) {
        return filters.selected_month;
    }
    const dateStr = filters?.end_date || filters?.start_date;
    if (dateStr) {
        const [y, m] = dateStr.split('-');
        if (y && m) return `${y}-${m}`;
    }
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
};

const ProdejnyPolozky = () => {
    const navigate = useNavigate();
    const leftFiltersRef = useRef(buildInitialPolozkyFilters());
    const [isComparison, setIsComparison] = useState(false);
    const [rightFilters, setRightFilters] = useState(() => shiftFiltersOneYearBack(buildInitialPolozkyFilters()));
    const [rightFiltersTouched, setRightFiltersTouched] = useState(false);
    const [visibleMetrics, setVisibleMetrics] = useState(() => new Set(DEFAULT_VISIBLE_METRICS));
    const [leftPaneData, setLeftPaneData] = useState(null);
    const [rightPaneData, setRightPaneData] = useState(null);
    const [compactDetail, setCompactDetail] = useState(false);
    const [sharedFilters, setSharedFilters] = useState(buildInitialPolozkyFilters());
    const [scopeFilters, setScopeFilters] = useState(() => pickPolozkyScope(buildInitialPolozkyFilters()));
    const [stores, setStores] = useState([]);

    useEffect(() => {
        storeAPI.getStoreChoices().then((data) => {
            const list = Array.isArray(data) ? data : data?.results || [];
            setStores(list);
        }).catch(() => setStores([]));
    }, []);

    const handleLeftFiltersChange = useCallback((next) => {
        leftFiltersRef.current = next;
        setSharedFilters(next);
        setScopeFilters(pickPolozkyScope(next));
    }, []);

    const handleRightFiltersChange = useCallback((next) => {
        setRightFiltersTouched(true);
        setRightFilters(next);
    }, []);

    const updateScope = useCallback((patch) => {
        setScopeFilters((prev) => {
            const nextScope = { ...prev, ...patch };
            const leftNext = mergePolozkyScope(leftFiltersRef.current, nextScope);
            leftFiltersRef.current = leftNext;
            setSharedFilters(leftNext);
            setRightFilters((rf) => mergePolozkyScope(rf, nextScope));
            return nextScope;
        });
    }, []);

    const toggleComparison = () => {
        setIsComparison((v) => {
            if (!v && !rightFiltersTouched) {
                setRightFilters(shiftFiltersOneYearBack(leftFiltersRef.current));
            }
            return !v;
        });
    };

    const openSellerCoaching = useCallback((seller) => {
        if (!seller?.id_prodejce) return;
        const mesic = mesicFromFilters(leftFiltersRef.current);
        navigate(`/coaching/seller/${seller.id_prodejce}?mesic=${mesic}`);
    }, [navigate]);

    return (
        <AnalyticsSectionWrapper title="Položky & výkony" icon="📱">
            <div className={`celkova-cisla-container polozky-container ${isComparison ? 'comparison-mode' : ''}`}>
                <div className="celkova-cisla-filters polozky-global-filters">
                    <div className="filter-row">
                        <PolozkyMetricPicker
                            visibleMetrics={visibleMetrics}
                            onChange={setVisibleMetrics}
                        />
                        <div className="filter-group polozky-compact-group">
                            <label className="polozky-compact-label">
                                <input
                                    type="checkbox"
                                    checked={compactDetail}
                                    onChange={(e) => setCompactDetail(e.target.checked)}
                                />
                                Menší ikonky detailu
                            </label>
                        </div>
                        <div className="filter-group">
                            <label>Kanál:</label>
                            <select
                                value={scopeFilters.kanal}
                                onChange={(e) => updateScope({ kanal: e.target.value })}
                            >
                                <option value="all">Všechny kanály</option>
                                <option value="prodejna">Prodejna</option>
                                <option value="eshop">E-shop</option>
                                <option value="allegro">ALLEGRO</option>
                                <option value="servis">Servis</option>
                            </select>
                        </div>
                        <div className="filter-group">
                            <label>Prodejna:</label>
                            <select
                                value={scopeFilters.prodejna_id || ''}
                                onChange={(e) => updateScope({ prodejna_id: e.target.value })}
                            >
                                <option value="">Všechny</option>
                                {stores.map((s) => (
                                    <option key={s.id || s.value} value={s.id || s.value}>
                                        {s.nazev || s.label || s.nazev_kratkiy}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                <div className="celkova-cisla-controls">
                    <p className="celkova-comparison-hint">
                        {isComparison
                            ? 'Vlevo a vpravo zvolte libovolné období. Pravý sloupec startuje stejným úsekem před rokem – můžete ho kdykoli změnit.'
                            : 'Srovnání zobrazí dvě období vedle sebe. Výchozí srovnání je stejné období loni, rozsah lze upravit. Kliknutím na kartu prodejce přejdete do modulu Výkony.'}
                    </p>
                    <button
                        type="button"
                        className={`comparison-toggle ${isComparison ? 'active' : ''}`}
                        onClick={toggleComparison}
                    >
                        {isComparison ? '🛑 Zrušit srovnání' : '🆚 Srovnání'}
                    </button>
                </div>

                <div className={`celkova-cisla-views${isComparison ? ' celkova-cisla-views--split' : ''}`}>
                    <div className="view-pane left-pane">
                        <ProdejnyPolozkyView
                            isComparison={isComparison}
                            paneRole="left"
                            scopeFilters={scopeFilters}
                            onFiltersChange={handleLeftFiltersChange}
                            compareData={isComparison ? rightPaneData : null}
                            onDataLoaded={setLeftPaneData}
                            onSellerClick={openSellerCoaching}
                            visibleMetrics={visibleMetrics}
                            compactDetail={compactDetail}
                        />
                    </div>
                    {isComparison && (
                        <div className="view-pane right-pane">
                            <ProdejnyPolozkyView
                                isComparison={isComparison}
                                paneRole="right"
                                scopeFilters={scopeFilters}
                                filtersFromParent={rightFilters}
                                onFiltersChange={handleRightFiltersChange}
                                compareData={leftPaneData}
                                onDataLoaded={setRightPaneData}
                                onSellerClick={openSellerCoaching}
                                visibleMetrics={visibleMetrics}
                                compactDetail={compactDetail}
                            />
                        </div>
                    )}
                </div>
            </div>
        </AnalyticsSectionWrapper>
    );
};

export default ProdejnyPolozky;
