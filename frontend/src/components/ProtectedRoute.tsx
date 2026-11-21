import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/useAuth";

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) return <main className="auth-loading"><div className="loading-line" /></main>;
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
