import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import DockNavbar from './DockNavbar';
import AppToast from './AppToast';
import UxFrictionMonitor from './UxFrictionMonitor';
import ProfileModule from '../modules/profile/ProfileModule';
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
const TasksManageModule = lazy(() => import('../modules/tasks/TasksManageModule'));

const RouteFallback = () => (
    <div className="dashboard-loading" role="status" aria-live="polite">
        Načítám modul…
    </div>
);

const Dashboard = () => {
    const { user, logout, isAdmin, canManageTasks } = useAuth();
    const { isDarkMode, toggleTheme } = useTheme();

    return (
        <div className="dashboard">
            <AppToast />
            <UxFrictionMonitor />
            <DockNavbar
                user={user}
                isAdmin={isAdmin}
                logout={logout}
                isDarkMode={isDarkMode}
                toggleTheme={toggleTheme}
            />

            <main className="dashboard-main">
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
                        <Route path="/plans" element={isAdmin() ? <PlansModule /> : <Navigate to="/" />} />
                        <Route path="/leaderboard" element={<LeaderboardModule />} />
                        <Route path="/profile" element={<ProfileModule />} />
                        <Route
                            path="/tasks"
                            element={canManageTasks() ? <TasksManageModule /> : <Navigate to="/" />}
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
            </main>
        </div>
    );
};

export default Dashboard;
