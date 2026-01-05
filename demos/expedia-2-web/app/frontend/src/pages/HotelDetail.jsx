import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Container from '../components/ui/Container';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import StarRating from '../components/results/StarRating';
import Price from '../components/results/Price';
import { getHotelById, listHotelRooms } from '../services/api';
import { useCart } from '../contexts/CartContext';
import { useToast } from '../components/ui/Toast';

export default function HotelDetail() {
  const { hotelId } = useParams();
  const [loading, setLoading] = useState(false);
  const [hotel, setHotel] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [error, setError] = useState('');
  const { addItem } = useCart();
  const toast = useToast();

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError('');
      try {
        const h = await getHotelById(hotelId);
        const r = await listHotelRooms(hotelId);
        if (!cancelled) {
          setHotel(h);
          setRooms(r.items || r);
        }
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Failed to load hotel');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [hotelId]);

  return (
    <Container className="py-8">
      <div className="mb-4 text-sm text-slate-600">
        <Link to="/stays" className="font-semibold text-brand-700 hover:underline">
          ← Back to results
        </Link>
      </div>

      {error ? <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}

      {loading || !hotel ? (
        <div className="grid place-items-center rounded-2xl border border-slate-200 bg-white p-10">
          <Spinner />
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <Card className="overflow-hidden">
              <div className="h-56 bg-slate-100 sm:h-72">
                {hotel.image_url ? (
                  <img src={hotel.image_url} alt={hotel.name} className="h-full w-full object-cover" />
                ) : (
                  <div className="h-full w-full bg-gradient-to-br from-brand-50 to-slate-100" />
                )}
              </div>
              <div className="p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="text-xs font-black text-brand-700">Hotel</div>
                    <div className="mt-1 text-2xl font-black text-slate-900">{hotel.name}</div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <StarRating rating={hotel.star_rating || hotel.rating || 0} />
                      {hotel.refundable ? <Badge variant="success">Refundable options</Badge> : null}
                    </div>
                    <div className="mt-2 text-sm text-slate-600">{hotel.address || hotel.city || ''}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-500">From</div>
                    <div className="text-2xl font-black text-slate-900">
                      <Price cents={hotel.price_per_night_cents || hotel.price_cents} />
                    </div>
                    <div className="text-xs text-slate-500">per night</div>
                  </div>
                </div>

                <div className="mt-6 text-sm text-slate-600">{hotel.description || 'A great place to stay with comfortable rooms and amenities.'}</div>
              </div>
            </Card>

            <div className="mt-6">
              <div className="mb-3 text-lg font-black text-slate-900">Choose a room</div>
              <div className="grid gap-4">
                {rooms.map((room) => (
                  <Card key={room.id} className="p-4">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <div className="text-base font-black text-slate-900">{room.name || 'Room'}</div>
                        <div className="mt-1 text-sm text-slate-600">{room.beds ? `${room.beds} bed(s)` : ''} {room.max_guests ? `• up to ${room.max_guests} guests` : ''}</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {room.refundable ? <Badge variant="success">Refundable</Badge> : <Badge>Non-refundable</Badge>}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-slate-500">Per night</div>
                        <div className="text-xl font-black text-slate-900">
                          <Price cents={room.price_per_night_cents || room.price_cents} />
                        </div>
                        <Button
                          className="mt-2"
                          onClick={async () => {
                            await addItem({
                              item_type: 'hotel',
                              hotel_id: hotel.id,
                              hotel_room_id: room.id,
                              // Backend requires dates; if not selected, default to a 1-night stay starting today.
                              start_date: new Date().toISOString().slice(0, 10),
                              end_date: new Date(Date.now() + 86400000).toISOString().slice(0, 10),
                              rooms: 1,
                              guests: 2
                            });
                            toast.success('Added room to cart');
                          }}
                        >
                          Add
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))}
                {rooms.length === 0 ? (
                  <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-600">
                    No rooms available.
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <div className="lg:col-span-4">
            <Card className="p-6">
              <div className="text-sm font-black text-slate-900">Your trip</div>
              <div className="mt-2 text-sm text-slate-600">Add this stay to your cart and checkout once.</div>
              <Button variant="secondary" className="mt-6 w-full" asChild>
                <Link to="/cart">Go to cart</Link>
              </Button>
            </Card>
          </div>
        </div>
      )}
    </Container>
  );
}
