import React from "react";
import { useAuth } from "../contexts/AuthContext";

const Dashboard: React.FC = () => {
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <main style={{ padding: "2rem" }}>
        <p>Loading your dashboard...</p>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main style={{ padding: "2rem" }}>
        <h1>Dashboard</h1>
        <p>You must be logged in to view this page.</p>
      </main>
    );
  }

  return (
    <main style={{ padding: "2rem" }}>
      <header style={{ marginBottom: "1.5rem" }}>
        <h1>Dashboard</h1>
        <p>
          Welcome{" "}
          {user?.full_name && user.full_name.trim().length > 0
            ? user.full_name
            : user?.email}
          !
        </p>
        <button
          type="button"
          onClick={logout}
          style={{
            marginTop: "0.75rem",
            padding: "0.5rem 1rem",
            cursor: "pointer",
          }}
        >
          Logout
        </button>
      </header>

      <section>
        <h2>Your Calendar Overview</h2>
        <p>
          This is the main dashboard area. Future enhancements can include your
          upcoming events, a monthly calendar view, and quick actions.
        </p>
      </section>
    </main>
  );
};

export default Dashboard;