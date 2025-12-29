// In-memory demo data used when DEMO_MODE=true or DB is unavailable.
// Keep this small but representative.

export const categories = [
  {
    id: 'beauty',
    name: 'Beauty & Personal Care',
    slug: 'beauty-personal-care',
    children: [
      {
        id: 'beauty-skin',
        name: 'Skin Care',
        slug: 'skin-care',
        children: [
          { id: 'beauty-skin-moist', name: 'Moisturizers', slug: 'moisturizers', children: [] },
          { id: 'beauty-skin-clean', name: 'Cleansers', slug: 'cleansers', children: [] }
        ]
      }
    ]
  },
  {
    id: 'electronics',
    name: 'Electronics',
    slug: 'electronics',
    children: [
      {
        id: 'electronics-audio',
        name: 'Audio',
        slug: 'audio',
        children: [
          { id: 'electronics-audio-hp', name: 'Headphones', slug: 'headphones', children: [] },
          { id: 'electronics-audio-sp', name: 'Speakers', slug: 'speakers', children: [] }
        ]
      },
      {
        id: 'electronics-tv',
        name: 'TV & Video',
        slug: 'tv-video',
        children: [
          { id: 'electronics-tv-stream', name: 'Streaming Devices', slug: 'streaming-devices', children: [] }
        ]
      }
    ]
  },
  {
    id: 'home',
    name: 'Home & Kitchen',
    slug: 'home-kitchen',
    children: [
      {
        id: 'home-coffee',
        name: 'Coffee & Tea',
        slug: 'coffee-tea',
        children: [
          { id: 'home-coffee-makers', name: 'Coffee Makers', slug: 'coffee-makers', children: [] }
        ]
      }
    ]
  }
];

export const products = [
  {
    id: 'p-1001',
    sku: 'EBAY-DEMO-1001',
    name: 'Hydrating Face Moisturizer (3.4oz)',
    price: 18.99,
    rating: 4.6,
    reviewCount: 1284,
    image: 'https://picsum.photos/seed/moisturizer/600/600',
    categoryPath: ['beauty-personal-care', 'skin-care', 'moisturizers'],
    shortDescription: 'Daily moisturizer with hyaluronic acid for all skin types.',
    description: 'A lightweight, fast-absorbing moisturizer formulated to hydrate and smooth skin.'
  },
  {
    id: 'p-1002',
    sku: 'EBAY-DEMO-1002',
    name: 'Gentle Facial Cleanser (8oz)',
    price: 12.5,
    rating: 4.3,
    reviewCount: 642,
    image: 'https://picsum.photos/seed/cleanser/600/600',
    categoryPath: ['beauty-personal-care', 'skin-care', 'cleansers'],
    shortDescription: 'Non-stripping cleanser for sensitive skin.',
    description: 'A creamy cleanser that removes dirt and makeup without drying your skin.'
  },
  {
    id: 'p-2001',
    sku: 'EBAY-DEMO-2001',
    name: 'Wireless Noise Cancelling Headphones',
    price: 129.99,
    rating: 4.7,
    reviewCount: 9876,
    image: 'https://picsum.photos/seed/headphones/600/600',
    categoryPath: ['electronics', 'audio', 'headphones'],
    shortDescription: 'Over-ear headphones with active noise cancelling.',
    description: 'Enjoy immersive sound with ANC, 30-hour battery, and quick charge.'
  },
  {
    id: 'p-2002',
    sku: 'EBAY-DEMO-2002',
    name: 'Portable Bluetooth Speaker',
    price: 49.99,
    rating: 4.4,
    reviewCount: 2310,
    image: 'https://picsum.photos/seed/speaker/600/600',
    categoryPath: ['electronics', 'audio', 'speakers'],
    shortDescription: 'Compact speaker with deep bass and 12-hour playtime.',
    description: 'Rugged, water-resistant speaker for indoor and outdoor listening.'
  },
  {
    id: 'p-2003',
    sku: 'EBAY-DEMO-2003',
    name: '4K Streaming Media Player',
    price: 39.0,
    rating: 4.2,
    reviewCount: 510,
    image: 'https://picsum.photos/seed/streamer/600/600',
    categoryPath: ['electronics', 'tv-video', 'streaming-devices'],
    shortDescription: 'Stream 4K HDR content with voice remote.',
    description: 'Fast performance, easy setup, and support for major streaming services.'
  },
  {
    id: 'p-3001',
    sku: 'EBAY-DEMO-3001',
    name: 'Programmable Coffee Maker (12-Cup)',
    price: 59.95,
    rating: 4.1,
    reviewCount: 1540,
    image: 'https://picsum.photos/seed/coffeemaker/600/600',
    categoryPath: ['home-kitchen', 'coffee-tea', 'coffee-makers'],
    shortDescription: 'Brew strength control and auto-start timer.',
    description: 'A reliable coffee maker with programmable timer and easy-clean carafe.'
  }
];

export const demoUser = {
  id: 'u-demo',
  name: 'Demo User',
  email: 'demo@example.com',
  newsletterSubscribed: true,
  addresses: {
    shipping: {
      name: 'Demo User',
      street1: '123 Market St',
      street2: 'Apt 4B',
      city: 'San Jose',
      region: 'CA',
      postalCode: '95113',
      country: 'US',
      phone: '555-0100'
    },
    billing: {
      name: 'Demo User',
      street1: '123 Market St',
      street2: 'Apt 4B',
      city: 'San Jose',
      region: 'CA',
      postalCode: '95113',
      country: 'US',
      phone: '555-0100'
    }
  },
  recentOrders: [
    {
      id: 'o-100000001',
      orderNumber: '100000001',
      date: '2025-01-15T10:00:00Z',
      shipTo: 'Demo User',
      orderTotal: 4497,
      status: 'Processing'
    }
  ]
};
