import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Protected } from "./components/Protected";
import { Spinner } from "./components/ui/Spinner";
import { AdminPage } from "./pages/AdminPage";
import { ChatPage } from "./pages/ChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SignupPage } from "./pages/SignupPage";

export default function App() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-zinc-500 dark:text-zinc-400">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/signup" element={user ? <Navigate to="/" replace /> : <SignupPage />} />
      <Route element={<Layout />}>
        <Route
          path="/"
          element={
            <Protected>
              <Navigate to="/chat" replace />
            </Protected>
          }
        />
        <Route
          path="/chat"
          element={
            <Protected>
              <ChatPage />
            </Protected>
          }
        />
        <Route
          path="/profile"
          element={
            <Protected>
              <ProfilePage />
            </Protected>
          }
        />
        <Route
          path="/dashboard"
          element={
            <Protected roles={["manager", "direction"]}>
              <DashboardPage />
            </Protected>
          }
        />
        <Route
          path="/admin"
          element={
            <Protected roles={["direction"]}>
              <AdminPage />
            </Protected>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
