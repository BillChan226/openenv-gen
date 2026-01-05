import React from 'react';
import { Toaster } from 'react-hot-toast';

export function ToastProvider({ children }) {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3500,
          style: {
            borderRadius: '14px',
            background: 'rgba(255,255,255,0.95)',
            color: '#111',
            boxShadow: '0 10px 30px rgba(0,0,0,0.12)',
          },
        }}
      />
      {children}
    </>
  );
}

export default ToastProvider;
