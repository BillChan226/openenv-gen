import React from 'react';
import TopNav from './TopNav';
import Footer from './Footer';

export default function AppShell({ children }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <TopNav />
      <main className="container-app py-8">{children}</main>
      <Footer />
    </div>
  );
}
