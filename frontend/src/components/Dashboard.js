import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import UserManagement from './UserManagement';
import CategoryManager from './CategoryManager';
import StoreManagement from './StoreManagement';
import DockNavbar from './DockNavbar';
import NewsModule from '../modules/news/NewsModule';
import AnalyticsModule from '../modules/analytics/AnalyticsModule';
import ProfileModule from '../modules/profile/ProfileModule';
import ShiftsModule from '../modules/shifts/ShiftsModule';
import AccessModule from '../modules/access/AccessModule';
import LeaderboardModule from '../modules/leaderboard/LeaderboardModule';
import OrdersModule from '../modules/orders/OrdersModule';
import PlansModule from '../modules/plans/PlansModule';
import TicketsModule from '../modules/tickets/TicketsModule';
import MyTickets from '../modules/tickets/MyTickets';
import './Dashboard.css';
import AdminDashboard from './AdminDashboard';
import SellerDashboard from './SellerDashboard';

const Dashboard = () => {
    const { user, logout, isAdmin } = useAuth();
    const { isDarkMode, toggleTheme } = useTheme();

    return (
        <div className="dashboard">
            <DockNavbar
                user={user}
                isAdmin={isAdmin}
                logout={logout}
                isDarkMode={isDarkMode}
                toggleTheme={toggleTheme}
            />

            <main className="dashboard-main">
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
                    
                    <Route path="/my-tickets" element={<MyTickets />} />

                    {/* Admin routes */}
                        {isAdmin() && (
                        <>
                            <Route path="/users" element={<UserManagement />} />
                            <Route path="/categories" element={<CategoryManager />} />
                            <Route path="/stores" element={<StoreManagement />} />
                            <Route path="/tickets" element={<TicketsModule />} />
                    </>
                )}
                </Routes>
            </main>
        </div>
    );
};

export default Dashboard; 
