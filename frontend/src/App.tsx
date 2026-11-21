import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { SiteLayout } from "./components/SiteLayout";
import { AuthProvider } from "./context/AuthContext";

const Landing = lazy(() => import("./pages/Landing").then((module) => ({ default: module.Landing })));
const Login = lazy(() => import("./pages/Login").then((module) => ({ default: module.Login })));
const Workspace = lazy(() => import("./pages/Workspace").then((module) => ({ default: module.Workspace })));
const History = lazy(() => import("./pages/History").then((module) => ({ default: module.History })));
const TaskDetail = lazy(() => import("./pages/TaskDetail").then((module) => ({ default: module.TaskDetail })));
const Tools = lazy(() => import("./pages/Tools").then((module) => ({ default: module.Tools })));
const Settings = lazy(() => import("./pages/Settings").then((module) => ({ default: module.Settings })));
const Documentation = lazy(() => import("./pages/Documentation").then((module) => ({ default: module.Documentation })));
const NotFound = lazy(() => import("./pages/NotFound").then((module) => ({ default: module.NotFound })));

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Suspense fallback={<main className="page-wrap"><div className="loading-line" /></main>}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<SiteLayout />}>
                <Route path="/workspace" element={<Workspace />} />
                <Route path="/tasks" element={<History />} />
                <Route path="/tasks/:id" element={<TaskDetail />} />
                <Route path="/tools" element={<Tools />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/docs" element={<Documentation />} />
                <Route path="/architecture" element={<Navigate to="/docs" replace />} />
                <Route path="/status" element={<Navigate to="/workspace" replace />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </ErrorBoundary>
  );
}
