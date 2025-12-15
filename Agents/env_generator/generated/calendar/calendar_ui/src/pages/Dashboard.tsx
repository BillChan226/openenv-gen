import React from "react";
import { Link } from "react-router-dom";

const Dashboard: React.FC = () => {
  // In a fuller implementation, user data would come from an AuthContext
  // or a similar provider. For now, this is a simple placeholder.
  const mockUser = {
    name: "Calendar User",
    email: "user@example.com",
  };

  return (
    <div className="page page-dashboard">
      <header className="dashboard-header">
        <div className="dashboard-header-left">
          <h1>Dashboard</h1>
          <p className="dashboard-subtitle">
            Welcome back, {mockUser.name}! Here&apos;s a quick overview of your calendar.
          </p>
        </div>
        <div className="dashboard-header-right">
          <div className="user-summary">
            <span className="user-name">{mockUser.name}</span>
            <span className="user-email">{mockUser.email}</span>
          </div>
          {/* Placeholder for a future logout button or user menu */}
        </div>
      </header>

      <main className="dashboard-main">
        <section className="dashboard-section">
          <h2>Quick Navigation</h2>
          <nav className="dashboard-nav">
            <ul>
              <li>
                <Link to="/calendar">View Calendar</Link>
              </li>
              <li>
                <Link to="/events/new">Create Event</Link>
              </li>
              <li>
                <Link to="/settings">Account Settings</Link>
              </li>
            </ul>
          </nav>
        </section>

        <section className="dashboard-section">
          <h2>Upcoming Events</h2>
          <p>
            Upcoming events will be shown here once the events API and calendar
            views are wired up.
          </p>
        </section>

        <section className="dashboard-section">
          <h2>Shared Calendars</h2>
          <p>
            Shared calendars and team schedules will appear here in a future
            iteration.
          </p>
        </section>
      </main>

      <footer className="dashboard-footer">
        <Link to="/">Back to home</Link>
      </footer>
    </div>
  );
};

export default Dashboard;