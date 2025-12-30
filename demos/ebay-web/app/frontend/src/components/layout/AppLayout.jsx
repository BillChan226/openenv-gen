import { Outlet } from 'react-router-dom';
import { Header } from './Header.jsx';
import { Footer } from './Footer.jsx';

export function AppLayout({ children }) {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="pb-12">{children || <Outlet />}</main>
      <Footer />
    </div>
  );
}
