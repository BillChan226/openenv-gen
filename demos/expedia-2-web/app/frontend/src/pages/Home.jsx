import React from 'react';
import Container from '../components/ui/Container';
import SearchTabs from '../components/search/SearchTabs';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';

export default function Home() {
  return (
    <div>
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-500 to-indigo-600">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-white blur-3xl" />
          <div className="absolute -bottom-24 -right-24 h-72 w-72 rounded-full bg-white blur-3xl" />
        </div>
        <Container className="relative py-10 sm:py-14">
          <div className="max-w-3xl">
            <Badge variant="blue" className="bg-white/15 text-white ring-white/20">
              Travel smarter
            </Badge>
            <h1 className="mt-4 text-3xl font-black tracking-tight text-white sm:text-5xl">
              Deals on flights, stays, cars, and bundles.
            </h1>
            <p className="mt-3 text-base text-white/85 sm:text-lg">
              Search and book in minutes. Keep everything in one cart, then checkout once.
            </p>
          </div>

          <div className="mt-8">
            <SearchTabs initialTab="stays" />
          </div>
        </Container>
      </section>

      <section className="py-10">
        <Container>
          <div className="grid gap-6 md:grid-cols-3">
            {[{
              title: 'Bundle & save',
              body: 'Combine a flight + hotel package to unlock better pricing.',
              tag: 'Packages'
            },
            {
              title: 'Flexible cancellation',
              body: 'Look for refundable options and manage cancellations in Trips.',
              tag: 'Trips'
            },
            {
              title: 'One cart, one checkout',
              body: 'Add flights, stays, and cars to a single cart and pay once.',
              tag: 'Cart'
            }].map((x) => (
              <Card key={x.title} className="p-6">
                <div className="text-xs font-black text-brand-700">{x.tag}</div>
                <div className="mt-2 text-lg font-black text-slate-900">{x.title}</div>
                <div className="mt-2 text-sm text-slate-600">{x.body}</div>
              </Card>
            ))}
          </div>
        </Container>
      </section>
    </div>
  );
}
