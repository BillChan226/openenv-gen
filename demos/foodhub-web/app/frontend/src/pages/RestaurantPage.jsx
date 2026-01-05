import React from 'react';
import { useParams } from 'react-router-dom';
import Store from './Store.jsx';

export function RestaurantPage() {
  const { restaurantId } = useParams();
  // Reuse existing Store page which expects storeId param.
  return <Store key={restaurantId} />;
}

export default RestaurantPage;
