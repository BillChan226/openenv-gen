import React from 'react';
import ReactDOM from 'react-dom/client';
import './App.css';
import App from './App';

// Create a root container for the React application
const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);

// Render the App component inside the root container
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);