import React from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

const Login: React.FC = () => {
  return (
    <main style={{ padding: "2rem" }}>
      <h1>Login</h1>
      <p>Please log in to access your calendar.</p>
    </main>
  );
};

const Register: React.FC = () => {
  return (
    <main style={{ padding: "2rem" }}>
      <h1>Register</h1>
      <p>Create an account to start using the calendar.</p>
    </main>
  );
};

const Dashboard: React.FC = () => {
  return (
    <main style={{ padding: "2rem" }}>
      <h1>Dashboard</h1>
      <p>Welcome to your calendar dashboard.</p>
    </main>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<Dashboard />} />
        {/* Fallback for unknown routes */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
tsx