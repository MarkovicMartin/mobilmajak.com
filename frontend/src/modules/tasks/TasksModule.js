import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { PageHeader } from '../../components/ui';
import TasksNav from './TasksNav';
import MyTasksModule from './MyTasksModule';
import TasksManageModule from './TasksManageModule';
import TasksWorkloadSection from './TasksWorkloadSection';
import { DEFAULT_TASKS_SECTION, tasksIdFromPath } from './tasksSections';
import './TasksModule.css';

const TasksModule = () => {
    const location = useLocation();
    const { isAdmin, canManageTasks } = useAuth();
    const sectionId = tasksIdFromPath(location.pathname);

    const guardManage = (element) => (
        canManageTasks() ? element : <Navigate to="/tasks/mine" replace />
    );

    const guardWorkload = (element) => (
        isAdmin() ? element : <Navigate to="/tasks/mine" replace />
    );

    return (
        <div className="tasks-module-shell">
            <PageHeader title="Úkoly" />
            <TasksNav />
            <div className="tasks-module-content">
                <Routes>
                    <Route index element={<Navigate to={`/tasks/${DEFAULT_TASKS_SECTION}`} replace />} />
                    <Route path="mine" element={<MyTasksModule embedded />} />
                    <Route path="manage" element={guardManage(<TasksManageModule embedded />)} />
                    <Route
                        path="workload"
                        element={guardWorkload(
                            <div className="tasks-workload-view">
                                <TasksWorkloadSection />
                            </div>,
                        )}
                    />
                    <Route
                        path="*"
                        element={<Navigate to={`/tasks/${sectionId || DEFAULT_TASKS_SECTION}`} replace />}
                    />
                </Routes>
            </div>
        </div>
    );
};

export default TasksModule;
