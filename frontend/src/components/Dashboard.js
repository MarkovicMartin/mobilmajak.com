import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import AppShell from './shell/AppShell';
import AppToast from './AppToast';
import UxFrictionMonitor from './UxFrictionMonitor';
import ProfileModule from '../modules/profile/ProfileModule';
import { FINANCE_MODULE_ENABLED, DAILY_DUTIES_MODULE_ENABLED } from '../config/featureFlags';
import './Dashboard.css';

const AdminDashboard = lazy(() => import('./AdminDashboard'));
const SellerDashboard = lazy(() => import('./SellerDashboard'));
const UserManagement = lazy(() => import('./UserManagement'));
const CategoryManager = lazy(() => import('./CategoryManager'));
const StoreManagement = lazy(() => import('./StoreManagement'));
const NewsModule = lazy(() => import('../modules/news/NewsModule'));
const AnalyticsModule = lazy(() => import('../modules/analytics/AnalyticsModule'));
const ShiftsModule = lazy(() => import('../modules/shifts/ShiftsModule'));
const AccessModule = lazy(() => import('../modules/access/AccessModule'));
const LeaderboardModule = lazy(() => import('../modules/leaderboard/LeaderboardModule'));
const OrdersModule = lazy(() => import('../modules/orders/OrdersModule'));
const PlansModule = lazy(() => import('../modules/plans/PlansModule'));
const TicketsModule = lazy(() => import('../modules/tickets/TicketsModule'));
const TasksModule = lazy(() => import('../modules/tasks/TasksModule'));
const CoachingModule = lazy(() => import('../modules/coaching/CoachingModule'));
const FinanceModule = FINANCE_MODULE_ENABLED
    ? lazy(() => import('../modules/finance/FinanceModule'))
    : null;
const WreckPartsModule = lazy(() => import('../modules/wreckParts/WreckPartsModule'));
const ReklamaceModule = lazy(() => import('../modules/reklamace/ReklamaceModule'));
const DailyDutiesModule = DAILY_DUTIES_MODULE_ENABLED
    ? lazy(() => import('../modules/dailyDuties/DailyDutiesModule'))
    : null;

const RouteFallback = () => (
    <div className="dashboard-loading" role="status" aria-live="polite">
        Načítám modul…
    </div>
);

const LegacyMyTasksRedirect = () => {
    const location = useLocation();
    return <Navigate to={`/tasks/mine${location.search}`} replace />;
};

const Dashboard = () => {
    const { user, logout, isAdmin, canManageTasks, canAccessCoaching } = useAuth();
    const { isDarkMode, toggleTheme } = useTheme();

    return (
        <>
            <AppToast />
            <UxFrictionMonitor />
            <AppShell
                user={user}
                isAdmin={isAdmin}
                canManageTasks={canManageTasks}
                canAccessCoaching={canAccessCoaching}
                logout={logout}
                isDarkMode={isDarkMode}
                toggleTheme={toggleTheme}
            >
                <Suspense fallback={<RouteFallback />}>
                    <Routes>
                        <Route path="/" element={ user?.role === 'ADMIN' ? (
                            <AdminDashboard />
                        ) : (
                            <SellerDashboard user={user} />
                        ) } />

                        <Route path="/news" element={<NewsModule />} />
                        <Route path="/analytics/*" element={isAdmin() ? <AnalyticsModule /> : <Navigate to="/" />} />
                        <Route path="/shifts" element={<ShiftsModule />} />
                        <Route path="/access" element={<AccessModule />} />
                        <Route path="/orders" element={<OrdersModule />} />
                        <Route path="/reklamace" element={<ReklamaceModule />} />
                        <Route path="/wreck-parts" element={<WreckPartsModule />} />
                        {DAILY_DUTIES_MODULE_ENABLED && (
                            <Route path="/daily-duties" element={<DailyDutiesModule />} />
                        )}
                        <Route path="/plans/*" element={isAdmin() ? <PlansModule /> : <Navigate to="/" />} />
                        {FINANCE_MODULE_ENABLED && (
                            <Route path="/finance/*" element={isAdmin() ? <FinanceModule /> : <Navigate to="/" />} />
                        )}
                        <Route path="/leaderboard" element={<LeaderboardModule />} />
                        <Route path="/profile" element={<ProfileModule />} />
                        <Route path="/tasks/*" element={<TasksModule />} />
                        <Route path="/my-tasks" element={<LegacyMyTasksRedirect />} />
                        <Route
                            path="/coaching/*"
                            element={canAccessCoaching() ? <CoachingModule /> : <Navigate to="/" />}
                        />

                        <Route path="/my-tickets" element={<TicketsModule />} />
                        <Route path="/tickets" element={<Navigate to="/my-tickets" replace />} />

                        {isAdmin() && (
                            <>
                                <Route path="/users" element={<UserManagement />} />
                                <Route path="/categories" element={<CategoryManager />} />
                                <Route path="/stores" element={<StoreManagement />} />
                            </>
                        )}
                    </Routes>
                </Suspense>
            </AppShell>
        </>
    );
};

export default Dashboard;
