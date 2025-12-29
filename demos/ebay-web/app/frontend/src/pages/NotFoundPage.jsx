import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="container-page py-16">
      <div className="mx-auto max-w-xl rounded-xl border bg-white p-8 text-center shadow-sm">
        <div className="text-5xl font-extrabold text-slate-900">404</div>
        <h1 className="mt-3 text-xl font-bold text-slate-900">Page not found</h1>
        <p className="mt-2 text-sm text-slate-600">
          The page you’re looking for doesn’t exist or was moved.
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Link
            to="/"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 focus-ring"
            data-testid="notfound-home"
          >
            Go home
          </Link>
          <Link
            to="/advanced-search"
            className="rounded-lg border px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 focus-ring"
            data-testid="notfound-advanced-search"
          >
            Advanced search
          </Link>
        </div>
      </div>
    </div>
  );
}
