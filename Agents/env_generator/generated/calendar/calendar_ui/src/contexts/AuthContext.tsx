import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (email: string, password: string, name: string) => Promise<void>;
}

interface User {
  id: string;
  name: string;
  email: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AuthProvider: React.FC<{children: ReactNode}> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Attempt to retrieve the user from localStorage
    const token = localStorage.getItem('token');
    if (token) {
      // Ideally, validate the token with the server to get the user info
      // For this example, we'll pretend it's decoded directly from the token
      const user = JSON.parse(atob(token.split('.')[1]));
      setUser(user);
    }
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // Perform login logic, typically an API call
      // This is a placeholder for actual authentication logic
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (response.ok) {
        const { token } = await response.json();
        localStorage.setItem('token', token);
        const user = JSON.parse(atob(token.split('.')[1]));
        setUser(user);
      } else {
        throw new Error('Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const register = async (email: string, password: string, name: string) => {
    try {
      // Perform registration logic, typically an API call
      // This is a placeholder for actual registration logic
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      });
      if (response.ok) {
        const { token } = await response.json();
        localStorage.setItem('token', token);
        const user = JSON.parse(atob(token.split('.')[1]));
        setUser(user);
      } else {
        throw new Error('Registration failed');
      }
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export { AuthProvider, useAuth };