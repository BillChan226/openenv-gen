import React from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
} from "react-router-dom";

const HomePage: React.FC = () => {
  return (
    <div className="page page-home">
      <h1>Calendar App</h1>
      <p>Welcome to the calendar application.</p>
      <nav>
        <ul>
          <li>
            <Link to="/login">Log in</Link>
          </li>
          <li>
            <Link to="/register">Register</Link>
          </li>
          <li>
            <Link to="/dashboard">Dashboard</Link>
          </li>
        </ul>
      </nav>
    </div>
  );
};

const LoginPage: React.FC = () => {
  return (
    <div className="page page-login">
      <h1>Log In</h1>
      <p>This is a placeholder login page.</p>
      <Link to="/">Back to home</Link>
    </div>
  );
};

const RegisterPage: React.FC = () => {
  return (
    <div className="page page-register">
      <h1>Register</h1>
      <p>This is a placeholder registration page.</p>
      <Link to="/">Back to home</Link>
    </div>
  );
};

const DashboardPage: React.FC = () => {
  return (
    <div className="page page-dashboard">
      <h1>Dashboard</h1>
      <p>This is a placeholder dashboard for the calendar.</p>
      <Link to="/">Back to home</Link>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;