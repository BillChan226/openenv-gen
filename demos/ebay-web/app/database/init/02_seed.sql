-- app/database/init/02_seed.sql
-- Deterministic seed data for ebay-web

BEGIN;

-- =========================
-- Users
-- =========================

-- All passwords are the same demo value (bcrypt hash for "password")
-- Hash: $2b$10$CwTycUXWue0Thq9StjUM0uJ8ZQxXh6uYqKqRR3vHyCuXapnwXCf9.

-- Requirement: seed exactly 1 demo user (with addresses) by default.
-- All passwords are the same demo value (bcrypt hash for "password").
INSERT INTO app_user (id, email, password_hash, first_name, last_name, newsletter_subscribed, role)
VALUES
  ('00000000-0000-0000-0000-000000000002', 'demo@example.com',  '$2b$10$CwTycUXWue0Thq9StjUM0uJ8ZQxXh6uYqKqRR3vHyCuXapnwXCf9.', 'Dana', 'Demo', TRUE, 'customer')
ON CONFLICT (id) DO NOTHING;

-- =========================
-- Addresses (for demo user)
-- =========================

INSERT INTO address (id, user_id, full_name, company, line1, line2, city, state, postal_code, country, phone)
VALUES
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 'Dana Demo', NULL, '123 Market St', 'Apt 5B', 'San Jose', 'CA', '95113', 'US', '408-555-0101'),
  ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'Dana Demo', 'Demo Co', '500 Shipping Ln', NULL, 'Austin', 'TX', '73301', 'US', '512-555-0199')
ON CONFLICT (id) DO NOTHING;

UPDATE app_user
SET default_billing_address_id = '10000000-0000-0000-0000-000000000001',
    default_shipping_address_id = '10000000-0000-0000-0000-000000000002'
WHERE id = '00000000-0000-0000-0000-000000000002';

-- =========================
-- Categories (12 top-level, 4 sub, 4 leaf each)
-- Slugs are unique across the tree.
-- =========================

-- Level 1
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('20000000-0000-0000-0000-000000000001','beauty-personal-care','Beauty & Personal Care',1,NULL),
  ('20000000-0000-0000-0000-000000000002','sports-outdoors','Sports & Outdoors',1,NULL),
  ('20000000-0000-0000-0000-000000000003','clothing-shoes-jewelry','Clothing, Shoes & Jewelry',1,NULL),
  ('20000000-0000-0000-0000-000000000004','home-kitchen','Home & Kitchen',1,NULL),
  ('20000000-0000-0000-0000-000000000005','office-products','Office Products',1,NULL),
  ('20000000-0000-0000-0000-000000000006','tools-home-improvement','Tools & Home Improvement',1,NULL),
  ('20000000-0000-0000-0000-000000000007','health-household','Health & Household',1,NULL),
  ('20000000-0000-0000-0000-000000000008','patio-lawn-garden','Patio, Lawn & Garden',1,NULL),
  ('20000000-0000-0000-0000-000000000009','electronics','Electronics',1,NULL),
  ('20000000-0000-0000-0000-000000000010','cell-phones-accessories','Cell Phones & Accessories',1,NULL),
  ('20000000-0000-0000-0000-000000000011','video-games','Video Games',1,NULL),
  ('20000000-0000-0000-0000-000000000012','grocery-gourmet-food','Grocery & Gourmet Food',1,NULL)
ON CONFLICT (id) DO NOTHING;

-- Level 2 and 3 helper: explicit inserts (deterministic)

-- Beauty & Personal Care
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('21000000-0000-0000-0000-000000000001','beauty-makeup','Makeup',2,'20000000-0000-0000-0000-000000000001'),
  ('21000000-0000-0000-0000-000000000002','beauty-skincare','Skincare',2,'20000000-0000-0000-0000-000000000001'),
  ('21000000-0000-0000-0000-000000000003','beauty-hair-care','Hair Care',2,'20000000-0000-0000-0000-000000000001'),
  ('21000000-0000-0000-0000-000000000004','beauty-fragrance','Fragrance',2,'20000000-0000-0000-0000-000000000001')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('21100000-0000-0000-0000-000000000001','beauty-makeup-face','Face',3,'21000000-0000-0000-0000-000000000001'),
  ('21100000-0000-0000-0000-000000000002','beauty-makeup-eyes','Eyes',3,'21000000-0000-0000-0000-000000000001'),
  ('21100000-0000-0000-0000-000000000003','beauty-makeup-lips','Lips',3,'21000000-0000-0000-0000-000000000001'),
  ('21100000-0000-0000-0000-000000000004','beauty-makeup-brushes','Brushes & Tools',3,'21000000-0000-0000-0000-000000000001'),
  ('21100000-0000-0000-0000-000000000005','beauty-skincare-cleansers','Cleansers',3,'21000000-0000-0000-0000-000000000002'),
  ('21100000-0000-0000-0000-000000000006','beauty-skincare-moisturizers','Moisturizers',3,'21000000-0000-0000-0000-000000000002'),
  ('21100000-0000-0000-0000-000000000007','beauty-skincare-sunscreen','Sunscreen',3,'21000000-0000-0000-0000-000000000002'),
  ('21100000-0000-0000-0000-000000000008','beauty-skincare-serums','Serums',3,'21000000-0000-0000-0000-000000000002'),
  ('21100000-0000-0000-0000-000000000009','beauty-hair-care-shampoo','Shampoo',3,'21000000-0000-0000-0000-000000000003'),
  ('21100000-0000-0000-0000-000000000010','beauty-hair-care-conditioner','Conditioner',3,'21000000-0000-0000-0000-000000000003'),
  ('21100000-0000-0000-0000-000000000011','beauty-hair-care-styling','Styling',3,'21000000-0000-0000-0000-000000000003'),
  ('21100000-0000-0000-0000-000000000012','beauty-hair-care-tools','Hair Tools',3,'21000000-0000-0000-0000-000000000003'),
  ('21100000-0000-0000-0000-000000000013','beauty-fragrance-women','Women''s Fragrance',3,'21000000-0000-0000-0000-000000000004'),
  ('21100000-0000-0000-0000-000000000014','beauty-fragrance-men','Men''s Fragrance',3,'21000000-0000-0000-0000-000000000004'),
  ('21100000-0000-0000-0000-000000000015','beauty-fragrance-sets','Gift Sets',3,'21000000-0000-0000-0000-000000000004'),
  ('21100000-0000-0000-0000-000000000016','beauty-fragrance-rollerball','Travel Size',3,'21000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Sports & Outdoors
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('22000000-0000-0000-0000-000000000001','sports-fitness','Fitness',2,'20000000-0000-0000-0000-000000000002'),
  ('22000000-0000-0000-0000-000000000002','sports-camping','Camping & Hiking',2,'20000000-0000-0000-0000-000000000002'),
  ('22000000-0000-0000-0000-000000000003','sports-cycling','Cycling',2,'20000000-0000-0000-0000-000000000002'),
  ('22000000-0000-0000-0000-000000000004','sports-water-sports','Water Sports',2,'20000000-0000-0000-0000-000000000002')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('22100000-0000-0000-0000-000000000001','sports-fitness-yoga','Yoga',3,'22000000-0000-0000-0000-000000000001'),
  ('22100000-0000-0000-0000-000000000002','sports-fitness-weights','Weights',3,'22000000-0000-0000-0000-000000000001'),
  ('22100000-0000-0000-0000-000000000003','sports-fitness-cardio','Cardio',3,'22000000-0000-0000-0000-000000000001'),
  ('22100000-0000-0000-0000-000000000004','sports-fitness-recovery','Recovery',3,'22000000-0000-0000-0000-000000000001'),
  ('22100000-0000-0000-0000-000000000005','sports-camping-tents','Tents',3,'22000000-0000-0000-0000-000000000002'),
  ('22100000-0000-0000-0000-000000000006','sports-camping-sleeping','Sleeping Bags',3,'22000000-0000-0000-0000-000000000002'),
  ('22100000-0000-0000-0000-000000000007','sports-camping-backpacks','Backpacks',3,'22000000-0000-0000-0000-000000000002'),
  ('22100000-0000-0000-0000-000000000008','sports-camping-stoves','Camp Kitchen',3,'22000000-0000-0000-0000-000000000002'),
  ('22100000-0000-0000-0000-000000000009','sports-cycling-helmets','Helmets',3,'22000000-0000-0000-0000-000000000003'),
  ('22100000-0000-0000-0000-000000000010','sports-cycling-lights','Lights',3,'22000000-0000-0000-0000-000000000003'),
  ('22100000-0000-0000-0000-000000000011','sports-cycling-tools','Tools',3,'22000000-0000-0000-0000-000000000003'),
  ('22100000-0000-0000-0000-000000000012','sports-cycling-accessories','Accessories',3,'22000000-0000-0000-0000-000000000003'),
  ('22100000-0000-0000-0000-000000000013','sports-water-sports-kayak','Kayaking',3,'22000000-0000-0000-0000-000000000004'),
  ('22100000-0000-0000-0000-000000000014','sports-water-sports-snorkel','Snorkeling',3,'22000000-0000-0000-0000-000000000004'),
  ('22100000-0000-0000-0000-000000000015','sports-water-sports-swim','Swim',3,'22000000-0000-0000-0000-000000000004'),
  ('22100000-0000-0000-0000-000000000016','sports-water-sports-surf','Surf',3,'22000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Clothing, Shoes & Jewelry
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('23000000-0000-0000-0000-000000000001','clothing-women','Women',2,'20000000-0000-0000-0000-000000000003'),
  ('23000000-0000-0000-0000-000000000002','clothing-men','Men',2,'20000000-0000-0000-0000-000000000003'),
  ('23000000-0000-0000-0000-000000000003','clothing-shoes','Shoes',2,'20000000-0000-0000-0000-000000000003'),
  ('23000000-0000-0000-0000-000000000004','clothing-jewelry','Jewelry',2,'20000000-0000-0000-0000-000000000003')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('23100000-0000-0000-0000-000000000001','clothing-women-tops','Tops',3,'23000000-0000-0000-0000-000000000001'),
  ('23100000-0000-0000-0000-000000000002','clothing-women-dresses','Dresses',3,'23000000-0000-0000-0000-000000000001'),
  ('23100000-0000-0000-0000-000000000003','clothing-women-activewear','Activewear',3,'23000000-0000-0000-0000-000000000001'),
  ('23100000-0000-0000-0000-000000000004','clothing-women-outerwear','Outerwear',3,'23000000-0000-0000-0000-000000000001'),
  ('23100000-0000-0000-0000-000000000005','clothing-men-shirts','Shirts',3,'23000000-0000-0000-0000-000000000002'),
  ('23100000-0000-0000-0000-000000000006','clothing-men-pants','Pants',3,'23000000-0000-0000-0000-000000000002'),
  ('23100000-0000-0000-0000-000000000007','clothing-men-activewear','Activewear',3,'23000000-0000-0000-0000-000000000002'),
  ('23100000-0000-0000-0000-000000000008','clothing-men-jackets','Jackets',3,'23000000-0000-0000-0000-000000000002'),
  ('23100000-0000-0000-0000-000000000009','clothing-shoes-sneakers','Sneakers',3,'23000000-0000-0000-0000-000000000003'),
  ('23100000-0000-0000-0000-000000000010','clothing-shoes-boots','Boots',3,'23000000-0000-0000-0000-000000000003'),
  ('23100000-0000-0000-0000-000000000011','clothing-shoes-sandals','Sandals',3,'23000000-0000-0000-0000-000000000003'),
  ('23100000-0000-0000-0000-000000000012','clothing-shoes-slippers','Slippers',3,'23000000-0000-0000-0000-000000000003'),
  ('23100000-0000-0000-0000-000000000013','clothing-jewelry-necklaces','Necklaces',3,'23000000-0000-0000-0000-000000000004'),
  ('23100000-0000-0000-0000-000000000014','clothing-jewelry-earrings','Earrings',3,'23000000-0000-0000-0000-000000000004'),
  ('23100000-0000-0000-0000-000000000015','clothing-jewelry-bracelets','Bracelets',3,'23000000-0000-0000-0000-000000000004'),
  ('23100000-0000-0000-0000-000000000016','clothing-jewelry-rings','Rings',3,'23000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Home & Kitchen
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('24000000-0000-0000-0000-000000000001','home-kitchen-bedding','Bedding',2,'20000000-0000-0000-0000-000000000004'),
  ('24000000-0000-0000-0000-000000000002','home-kitchen-kitchen-dining','Kitchen & Dining',2,'20000000-0000-0000-0000-000000000004'),
  ('24000000-0000-0000-0000-000000000003','home-kitchen-storage','Storage & Organization',2,'20000000-0000-0000-0000-000000000004'),
  ('24000000-0000-0000-0000-000000000004','home-kitchen-decor','Home Decor',2,'20000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('24100000-0000-0000-0000-000000000001','home-kitchen-bedding-sheets','Sheets',3,'24000000-0000-0000-0000-000000000001'),
  ('24100000-0000-0000-0000-000000000002','home-kitchen-bedding-pillows','Pillows',3,'24000000-0000-0000-0000-000000000001'),
  ('24100000-0000-0000-0000-000000000003','home-kitchen-bedding-comforters','Comforters',3,'24000000-0000-0000-0000-000000000001'),
  ('24100000-0000-0000-0000-000000000004','home-kitchen-bedding-mattress','Mattress Pads',3,'24000000-0000-0000-0000-000000000001'),
  ('24100000-0000-0000-0000-000000000005','home-kitchen-kitchen-dining-cookware','Cookware',3,'24000000-0000-0000-0000-000000000002'),
  ('24100000-0000-0000-0000-000000000006','home-kitchen-kitchen-dining-coffee','Coffee & Tea',3,'24000000-0000-0000-0000-000000000002'),
  ('24100000-0000-0000-0000-000000000007','home-kitchen-kitchen-dining-appliances','Small Appliances',3,'24000000-0000-0000-0000-000000000002'),
  ('24100000-0000-0000-0000-000000000008','home-kitchen-kitchen-dining-tableware','Tableware',3,'24000000-0000-0000-0000-000000000002'),
  ('24100000-0000-0000-0000-000000000009','home-kitchen-storage-containers','Containers',3,'24000000-0000-0000-0000-000000000003'),
  ('24100000-0000-0000-0000-000000000010','home-kitchen-storage-closet','Closet Storage',3,'24000000-0000-0000-0000-000000000003'),
  ('24100000-0000-0000-0000-000000000011','home-kitchen-storage-laundry','Laundry',3,'24000000-0000-0000-0000-000000000003'),
  ('24100000-0000-0000-0000-000000000012','home-kitchen-storage-shelving','Shelving',3,'24000000-0000-0000-0000-000000000003'),
  ('24100000-0000-0000-0000-000000000013','home-kitchen-decor-wall','Wall Decor',3,'24000000-0000-0000-0000-000000000004'),
  ('24100000-0000-0000-0000-000000000014','home-kitchen-decor-rugs','Rugs',3,'24000000-0000-0000-0000-000000000004'),
  ('24100000-0000-0000-0000-000000000015','home-kitchen-decor-lighting','Lighting',3,'24000000-0000-0000-0000-000000000004'),
  ('24100000-0000-0000-0000-000000000016','home-kitchen-decor-candles','Candles',3,'24000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Office Products
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('25000000-0000-0000-0000-000000000001','office-writing','Writing',2,'20000000-0000-0000-0000-000000000005'),
  ('25000000-0000-0000-0000-000000000002','office-paper','Paper',2,'20000000-0000-0000-0000-000000000005'),
  ('25000000-0000-0000-0000-000000000003','office-desk-accessories','Desk Accessories',2,'20000000-0000-0000-0000-000000000005'),
  ('25000000-0000-0000-0000-000000000004','office-printers','Printers & Ink',2,'20000000-0000-0000-0000-000000000005')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('25100000-0000-0000-0000-000000000001','office-writing-pens','Pens',3,'25000000-0000-0000-0000-000000000001'),
  ('25100000-0000-0000-0000-000000000002','office-writing-pencils','Pencils',3,'25000000-0000-0000-0000-000000000001'),
  ('25100000-0000-0000-0000-000000000003','office-writing-markers','Markers',3,'25000000-0000-0000-0000-000000000001'),
  ('25100000-0000-0000-0000-000000000004','office-writing-highlighters','Highlighters',3,'25000000-0000-0000-0000-000000000001'),
  ('25100000-0000-0000-0000-000000000005','office-paper-notebooks','Notebooks',3,'25000000-0000-0000-0000-000000000002'),
  ('25100000-0000-0000-0000-000000000006','office-paper-printer-paper','Printer Paper',3,'25000000-0000-0000-0000-000000000002'),
  ('25100000-0000-0000-0000-000000000007','office-paper-sticky-notes','Sticky Notes',3,'25000000-0000-0000-0000-000000000002'),
  ('25100000-0000-0000-0000-000000000008','office-paper-folders','Folders',3,'25000000-0000-0000-0000-000000000002'),
  ('25100000-0000-0000-0000-000000000009','office-desk-accessories-organizers','Organizers',3,'25000000-0000-0000-0000-000000000003'),
  ('25100000-0000-0000-0000-000000000010','office-desk-accessories-chairs','Office Chairs',3,'25000000-0000-0000-0000-000000000003'),
  ('25100000-0000-0000-0000-000000000011','office-desk-accessories-lamps','Desk Lamps',3,'25000000-0000-0000-0000-000000000003'),
  ('25100000-0000-0000-0000-000000000012','office-desk-accessories-storage','File Storage',3,'25000000-0000-0000-0000-000000000003'),
  ('25100000-0000-0000-0000-000000000013','office-printers-ink','Ink & Toner',3,'25000000-0000-0000-0000-000000000004'),
  ('25100000-0000-0000-0000-000000000014','office-printers-laser','Laser Printers',3,'25000000-0000-0000-0000-000000000004'),
  ('25100000-0000-0000-0000-000000000015','office-printers-label','Label Printers',3,'25000000-0000-0000-0000-000000000004'),
  ('25100000-0000-0000-0000-000000000016','office-printers-3d','3D Printers',3,'25000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Tools & Home Improvement
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('26000000-0000-0000-0000-000000000001','tools-power-tools','Power Tools',2,'20000000-0000-0000-0000-000000000006'),
  ('26000000-0000-0000-0000-000000000002','tools-hand-tools','Hand Tools',2,'20000000-0000-0000-0000-000000000006'),
  ('26000000-0000-0000-0000-000000000003','tools-hardware','Hardware',2,'20000000-0000-0000-0000-000000000006'),
  ('26000000-0000-0000-0000-000000000004','tools-lighting','Lighting & Electrical',2,'20000000-0000-0000-0000-000000000006')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('26100000-0000-0000-0000-000000000001','tools-power-tools-drills','Drills',3,'26000000-0000-0000-0000-000000000001'),
  ('26100000-0000-0000-0000-000000000002','tools-power-tools-saws','Saws',3,'26000000-0000-0000-0000-000000000001'),
  ('26100000-0000-0000-0000-000000000003','tools-power-tools-sanders','Sanders',3,'26000000-0000-0000-0000-000000000001'),
  ('26100000-0000-0000-0000-000000000004','tools-power-tools-air','Air Tools',3,'26000000-0000-0000-0000-000000000001'),
  ('26100000-0000-0000-0000-000000000005','tools-hand-tools-wrenches','Wrenches',3,'26000000-0000-0000-0000-000000000002'),
  ('26100000-0000-0000-0000-000000000006','tools-hand-tools-screwdrivers','Screwdrivers',3,'26000000-0000-0000-0000-000000000002'),
  ('26100000-0000-0000-0000-000000000007','tools-hand-tools-pliers','Pliers',3,'26000000-0000-0000-0000-000000000002'),
  ('26100000-0000-0000-0000-000000000008','tools-hand-tools-hammers','Hammers',3,'26000000-0000-0000-0000-000000000002'),
  ('26100000-0000-0000-0000-000000000009','tools-hardware-fasteners','Fasteners',3,'26000000-0000-0000-0000-000000000003'),
  ('26100000-0000-0000-0000-000000000010','tools-hardware-adhesives','Adhesives',3,'26000000-0000-0000-0000-000000000003'),
  ('26100000-0000-0000-0000-000000000011','tools-hardware-door','Door Hardware',3,'26000000-0000-0000-0000-000000000003'),
  ('26100000-0000-0000-0000-000000000012','tools-hardware-cabinet','Cabinet Hardware',3,'26000000-0000-0000-0000-000000000003'),
  ('26100000-0000-0000-0000-000000000013','tools-lighting-bulbs','Light Bulbs',3,'26000000-0000-0000-0000-000000000004'),
  ('26100000-0000-0000-0000-000000000014','tools-lighting-switches','Switches',3,'26000000-0000-0000-0000-000000000004'),
  ('26100000-0000-0000-0000-000000000015','tools-lighting-outlets','Outlets',3,'26000000-0000-0000-0000-000000000004'),
  ('26100000-0000-0000-0000-000000000016','tools-lighting-smart','Smart Lighting',3,'26000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Health & Household
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('27000000-0000-0000-0000-000000000001','health-vitamins','Vitamins & Supplements',2,'20000000-0000-0000-0000-000000000007'),
  ('27000000-0000-0000-0000-000000000002','health-personal-care','Personal Care',2,'20000000-0000-0000-0000-000000000007'),
  ('27000000-0000-0000-0000-000000000003','health-household-supplies','Household Supplies',2,'20000000-0000-0000-0000-000000000007'),
  ('27000000-0000-0000-0000-000000000004','health-baby','Baby',2,'20000000-0000-0000-0000-000000000007')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('27100000-0000-0000-0000-000000000001','health-vitamins-multivitamins','Multivitamins',3,'27000000-0000-0000-0000-000000000001'),
  ('27100000-0000-0000-0000-000000000002','health-vitamins-protein','Protein',3,'27000000-0000-0000-0000-000000000001'),
  ('27100000-0000-0000-0000-000000000003','health-vitamins-omega','Omega-3',3,'27000000-0000-0000-0000-000000000001'),
  ('27100000-0000-0000-0000-000000000004','health-vitamins-probiotics','Probiotics',3,'27000000-0000-0000-0000-000000000001'),
  ('27100000-0000-0000-0000-000000000005','health-personal-care-oral','Oral Care',3,'27000000-0000-0000-0000-000000000002'),
  ('27100000-0000-0000-0000-000000000006','health-personal-care-body','Body Care',3,'27000000-0000-0000-0000-000000000002'),
  ('27100000-0000-0000-0000-000000000007','health-personal-care-shaving','Shaving',3,'27000000-0000-0000-0000-000000000002'),
  ('27100000-0000-0000-0000-000000000008','health-personal-care-feminine','Feminine Care',3,'27000000-0000-0000-0000-000000000002'),
  ('27100000-0000-0000-0000-000000000009','health-household-supplies-laundry','Laundry',3,'27000000-0000-0000-0000-000000000003'),
  ('27100000-0000-0000-0000-000000000010','health-household-supplies-cleaning','Cleaning',3,'27000000-0000-0000-0000-000000000003'),
  ('27100000-0000-0000-0000-000000000011','health-household-supplies-paper','Paper Goods',3,'27000000-0000-0000-0000-000000000003'),
  ('27100000-0000-0000-0000-000000000012','health-household-supplies-disposable','Disposable',3,'27000000-0000-0000-0000-000000000003'),
  ('27100000-0000-0000-0000-000000000013','health-baby-diapers','Diapers',3,'27000000-0000-0000-0000-000000000004'),
  ('27100000-0000-0000-0000-000000000014','health-baby-wipes','Wipes',3,'27000000-0000-0000-0000-000000000004'),
  ('27100000-0000-0000-0000-000000000015','health-baby-feeding','Feeding',3,'27000000-0000-0000-0000-000000000004'),
  ('27100000-0000-0000-0000-000000000016','health-baby-gear','Gear',3,'27000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Patio, Lawn & Garden
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('28000000-0000-0000-0000-000000000001','garden-outdoor-decor','Outdoor Decor',2,'20000000-0000-0000-0000-000000000008'),
  ('28000000-0000-0000-0000-000000000002','garden-grilling','Grilling',2,'20000000-0000-0000-0000-000000000008'),
  ('28000000-0000-0000-0000-000000000003','garden-gardening','Gardening',2,'20000000-0000-0000-0000-000000000008'),
  ('28000000-0000-0000-0000-000000000004','garden-patio-furniture','Patio Furniture',2,'20000000-0000-0000-0000-000000000008')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('28100000-0000-0000-0000-000000000001','garden-outdoor-decor-lights','Outdoor Lights',3,'28000000-0000-0000-0000-000000000001'),
  ('28100000-0000-0000-0000-000000000002','garden-outdoor-decor-planters','Planters',3,'28000000-0000-0000-0000-000000000001'),
  ('28100000-0000-0000-0000-000000000003','garden-outdoor-decor-rugs','Outdoor Rugs',3,'28000000-0000-0000-0000-000000000001'),
  ('28100000-0000-0000-0000-000000000004','garden-outdoor-decor-fire','Fire Pits',3,'28000000-0000-0000-0000-000000000001'),
  ('28100000-0000-0000-0000-000000000005','garden-grilling-grills','Grills',3,'28000000-0000-0000-0000-000000000002'),
  ('28100000-0000-0000-0000-000000000006','garden-grilling-tools','Grill Tools',3,'28000000-0000-0000-0000-000000000002'),
  ('28100000-0000-0000-0000-000000000007','garden-grilling-fuel','Charcoal & Fuel',3,'28000000-0000-0000-0000-000000000002'),
  ('28100000-0000-0000-0000-000000000008','garden-grilling-accessories','Accessories',3,'28000000-0000-0000-0000-000000000002'),
  ('28100000-0000-0000-0000-000000000009','garden-gardening-tools','Garden Tools',3,'28000000-0000-0000-0000-000000000003'),
  ('28100000-0000-0000-0000-000000000010','garden-gardening-soil','Soil & Fertilizer',3,'28000000-0000-0000-0000-000000000003'),
  ('28100000-0000-0000-0000-000000000011','garden-gardening-watering','Watering',3,'28000000-0000-0000-0000-000000000003'),
  ('28100000-0000-0000-0000-000000000012','garden-gardening-seeds','Seeds',3,'28000000-0000-0000-0000-000000000003'),
  ('28100000-0000-0000-0000-000000000013','garden-patio-furniture-chairs','Chairs',3,'28000000-0000-0000-0000-000000000004'),
  ('28100000-0000-0000-0000-000000000014','garden-patio-furniture-tables','Tables',3,'28000000-0000-0000-0000-000000000004'),
  ('28100000-0000-0000-0000-000000000015','garden-patio-furniture-sets','Sets',3,'28000000-0000-0000-0000-000000000004'),
  ('28100000-0000-0000-0000-000000000016','garden-patio-furniture-umbrellas','Umbrellas',3,'28000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Electronics
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('29000000-0000-0000-0000-000000000001','electronics-computers','Computers',2,'20000000-0000-0000-0000-000000000009'),
  ('29000000-0000-0000-0000-000000000002','electronics-tv-home-theater','TV & Home Theater',2,'20000000-0000-0000-0000-000000000009'),
  ('29000000-0000-0000-0000-000000000003','electronics-audio','Audio',2,'20000000-0000-0000-0000-000000000009'),
  ('29000000-0000-0000-0000-000000000004','electronics-cameras','Cameras',2,'20000000-0000-0000-0000-000000000009')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('29100000-0000-0000-0000-000000000001','electronics-computers-laptops','Laptops',3,'29000000-0000-0000-0000-000000000001'),
  ('29100000-0000-0000-0000-000000000002','electronics-computers-desktops','Desktops',3,'29000000-0000-0000-0000-000000000001'),
  ('29100000-0000-0000-0000-000000000003','electronics-computers-monitors','Monitors',3,'29000000-0000-0000-0000-000000000001'),
  ('29100000-0000-0000-0000-000000000004','electronics-computers-accessories','Computer Accessories',3,'29000000-0000-0000-0000-000000000001'),
  ('29100000-0000-0000-0000-000000000005','electronics-tv-home-theater-tvs','Televisions',3,'29000000-0000-0000-0000-000000000002'),
  ('29100000-0000-0000-0000-000000000006','electronics-tv-home-theater-streaming','Streaming Devices',3,'29000000-0000-0000-0000-000000000002'),
  ('29100000-0000-0000-0000-000000000007','electronics-tv-home-theater-soundbars','Soundbars',3,'29000000-0000-0000-0000-000000000002'),
  ('29100000-0000-0000-0000-000000000008','electronics-tv-home-theater-projectors','Projectors',3,'29000000-0000-0000-0000-000000000002'),
  ('29100000-0000-0000-0000-000000000009','electronics-audio-headphones','Headphones',3,'29000000-0000-0000-0000-000000000003'),
  ('29100000-0000-0000-0000-000000000010','electronics-audio-speakers','Speakers',3,'29000000-0000-0000-0000-000000000003'),
  ('29100000-0000-0000-0000-000000000011','electronics-audio-turntables','Turntables',3,'29000000-0000-0000-0000-000000000003'),
  ('29100000-0000-0000-0000-000000000012','electronics-audio-microphones','Microphones',3,'29000000-0000-0000-0000-000000000003'),
  ('29100000-0000-0000-0000-000000000013','electronics-cameras-mirrorless','Mirrorless',3,'29000000-0000-0000-0000-000000000004'),
  ('29100000-0000-0000-0000-000000000014','electronics-cameras-dslr','DSLR',3,'29000000-0000-0000-0000-000000000004'),
  ('29100000-0000-0000-0000-000000000015','electronics-cameras-action','Action Cameras',3,'29000000-0000-0000-0000-000000000004'),
  ('29100000-0000-0000-0000-000000000016','electronics-cameras-lenses','Lenses',3,'29000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Cell Phones & Accessories
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('30000000-0000-0000-0000-000000000001','phones-smartphones','Smartphones',2,'20000000-0000-0000-0000-000000000010'),
  ('30000000-0000-0000-0000-000000000002','phones-cases','Cases',2,'20000000-0000-0000-0000-000000000010'),
  ('30000000-0000-0000-0000-000000000003','phones-chargers','Chargers',2,'20000000-0000-0000-0000-000000000010'),
  ('30000000-0000-0000-0000-000000000004','phones-audio','Mobile Audio',2,'20000000-0000-0000-0000-000000000010')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('30100000-0000-0000-0000-000000000001','phones-smartphones-android','Android Phones',3,'30000000-0000-0000-0000-000000000001'),
  ('30100000-0000-0000-0000-000000000002','phones-smartphones-ios','iOS Phones',3,'30000000-0000-0000-0000-000000000001'),
  ('30100000-0000-0000-0000-000000000003','phones-smartphones-unlocked','Unlocked',3,'30000000-0000-0000-0000-000000000001'),
  ('30100000-0000-0000-0000-000000000004','phones-smartphones-refurb','Refurbished',3,'30000000-0000-0000-0000-000000000001'),
  ('30100000-0000-0000-0000-000000000005','phones-cases-rugged','Rugged Cases',3,'30000000-0000-0000-0000-000000000002'),
  ('30100000-0000-0000-0000-000000000006','phones-cases-clear','Clear Cases',3,'30000000-0000-0000-0000-000000000002'),
  ('30100000-0000-0000-0000-000000000007','phones-cases-wallet','Wallet Cases',3,'30000000-0000-0000-0000-000000000002'),
  ('30100000-0000-0000-0000-000000000008','phones-cases-magsafe','MagSafe',3,'30000000-0000-0000-0000-000000000002'),
  ('30100000-0000-0000-0000-000000000009','phones-chargers-wall','Wall Chargers',3,'30000000-0000-0000-0000-000000000003'),
  ('30100000-0000-0000-0000-000000000010','phones-chargers-wireless','Wireless Chargers',3,'30000000-0000-0000-0000-000000000003'),
  ('30100000-0000-0000-0000-000000000011','phones-chargers-car','Car Chargers',3,'30000000-0000-0000-0000-000000000003'),
  ('30100000-0000-0000-0000-000000000012','phones-chargers-cables','Cables',3,'30000000-0000-0000-0000-000000000003'),
  ('30100000-0000-0000-0000-000000000013','phones-audio-earbuds','Earbuds',3,'30000000-0000-0000-0000-000000000004'),
  ('30100000-0000-0000-0000-000000000014','phones-audio-headsets','Headsets',3,'30000000-0000-0000-0000-000000000004'),
  ('30100000-0000-0000-0000-000000000015','phones-audio-adapters','Adapters',3,'30000000-0000-0000-0000-000000000004'),
  ('30100000-0000-0000-0000-000000000016','phones-audio-speakers','Portable Speakers',3,'30000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Video Games
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('31000000-0000-0000-0000-000000000001','games-consoles','Consoles',2,'20000000-0000-0000-0000-000000000011'),
  ('31000000-0000-0000-0000-000000000002','games-accessories','Accessories',2,'20000000-0000-0000-0000-000000000011'),
  ('31000000-0000-0000-0000-000000000003','games-games','Games',2,'20000000-0000-0000-0000-000000000011'),
  ('31000000-0000-0000-0000-000000000004','games-pc','PC Gaming',2,'20000000-0000-0000-0000-000000000011')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('31100000-0000-0000-0000-000000000001','games-consoles-playstation','PlayStation',3,'31000000-0000-0000-0000-000000000001'),
  ('31100000-0000-0000-0000-000000000002','games-consoles-xbox','Xbox',3,'31000000-0000-0000-0000-000000000001'),
  ('31100000-0000-0000-0000-000000000003','games-consoles-nintendo','Nintendo',3,'31000000-0000-0000-0000-000000000001'),
  ('31100000-0000-0000-0000-000000000004','games-consoles-handheld','Handheld',3,'31000000-0000-0000-0000-000000000001'),
  ('31100000-0000-0000-0000-000000000005','games-accessories-controllers','Controllers',3,'31000000-0000-0000-0000-000000000002'),
  ('31100000-0000-0000-0000-000000000006','games-accessories-headsets','Headsets',3,'31000000-0000-0000-0000-000000000002'),
  ('31100000-0000-0000-0000-000000000007','games-accessories-storage','Storage',3,'31000000-0000-0000-0000-000000000002'),
  ('31100000-0000-0000-0000-000000000008','games-accessories-charging','Charging Docks',3,'31000000-0000-0000-0000-000000000002'),
  ('31100000-0000-0000-0000-000000000009','games-games-action','Action',3,'31000000-0000-0000-0000-000000000003'),
  ('31100000-0000-0000-0000-000000000010','games-games-rpg','RPG',3,'31000000-0000-0000-0000-000000000003'),
  ('31100000-0000-0000-0000-000000000011','games-games-sports','Sports',3,'31000000-0000-0000-0000-000000000003'),
  ('31100000-0000-0000-0000-000000000012','games-games-family','Family',3,'31000000-0000-0000-0000-000000000003'),
  ('31100000-0000-0000-0000-000000000013','games-pc-mice','Gaming Mice',3,'31000000-0000-0000-0000-000000000004'),
  ('31100000-0000-0000-0000-000000000014','games-pc-keyboards','Keyboards',3,'31000000-0000-0000-0000-000000000004'),
  ('31100000-0000-0000-0000-000000000015','games-pc-chairs','Gaming Chairs',3,'31000000-0000-0000-0000-000000000004'),
  ('31100000-0000-0000-0000-000000000016','games-pc-headsets','PC Headsets',3,'31000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- Grocery & Gourmet Food
INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('32000000-0000-0000-0000-000000000001','grocery-beverages','Beverages',2,'20000000-0000-0000-0000-000000000012'),
  ('32000000-0000-0000-0000-000000000002','grocery-snacks','Snacks',2,'20000000-0000-0000-0000-000000000012'),
  ('32000000-0000-0000-0000-000000000003','grocery-coffee-tea','Coffee & Tea',2,'20000000-0000-0000-0000-000000000012'),
  ('32000000-0000-0000-0000-000000000004','grocery-pantry','Pantry Staples',2,'20000000-0000-0000-0000-000000000012')
ON CONFLICT (id) DO NOTHING;

INSERT INTO category (id, slug, name, level, parent_id) VALUES
  ('32100000-0000-0000-0000-000000000001','grocery-beverages-sparkling','Sparkling Water',3,'32000000-0000-0000-0000-000000000001'),
  ('32100000-0000-0000-0000-000000000002','grocery-beverages-soda','Soda',3,'32000000-0000-0000-0000-000000000001'),
  ('32100000-0000-0000-0000-000000000003','grocery-beverages-juice','Juice',3,'32000000-0000-0000-0000-000000000001'),
  ('32100000-0000-0000-0000-000000000004','grocery-beverages-energy','Energy Drinks',3,'32000000-0000-0000-0000-000000000001'),
  ('32100000-0000-0000-0000-000000000005','grocery-snacks-chips','Chips',3,'32000000-0000-0000-0000-000000000002'),
  ('32100000-0000-0000-0000-000000000006','grocery-snacks-chocolate','Chocolate',3,'32000000-0000-0000-0000-000000000002'),
  ('32100000-0000-0000-0000-000000000007','grocery-snacks-nuts','Nuts',3,'32000000-0000-0000-0000-000000000002'),
  ('32100000-0000-0000-0000-000000000008','grocery-snacks-cookies','Cookies',3,'32000000-0000-0000-0000-000000000002'),
  ('32100000-0000-0000-0000-000000000009','grocery-coffee-tea-coffee','Coffee',3,'32000000-0000-0000-0000-000000000003'),
  ('32100000-0000-0000-0000-000000000010','grocery-coffee-tea-tea','Tea',3,'32000000-0000-0000-0000-000000000003'),
  ('32100000-0000-0000-0000-000000000011','grocery-coffee-tea-kpods','K-Cups',3,'32000000-0000-0000-0000-000000000003'),
  ('32100000-0000-0000-0000-000000000012','grocery-coffee-tea-creamers','Creamers',3,'32000000-0000-0000-0000-000000000003'),
  ('32100000-0000-0000-0000-000000000013','grocery-pantry-pasta','Pasta',3,'32000000-0000-0000-0000-000000000004'),
  ('32100000-0000-0000-0000-000000000014','grocery-pantry-rice','Rice',3,'32000000-0000-0000-0000-000000000004'),
  ('32100000-0000-0000-0000-000000000015','grocery-pantry-sauces','Sauces',3,'32000000-0000-0000-0000-000000000004'),
  ('32100000-0000-0000-0000-000000000016','grocery-pantry-spices','Spices',3,'32000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO NOTHING;

-- =========================
-- Products (60) + product_category mapping
-- =========================

-- Use predictable UUIDs per product for stable references.

INSERT INTO product (id, sku, name, price_cents, currency, rating, review_count, primary_image_url, short_description, description, attributes, inventory_status)
VALUES
  ('40000000-0000-0000-0000-000000000001','BEA-FACE-001','Hydrating Liquid Foundation - Medium',2799,'USD',4.4,128,'https://picsum.photos/seed/BEA-FACE-001/600/600','Lightweight, buildable coverage with a natural finish.','A hydrating foundation designed for all-day wear. Blends easily and helps even skin tone without feeling heavy.','{"shade":"Medium","finish":"Natural"}','in_stock'),
  ('40000000-0000-0000-0000-000000000002','BEA-EYES-002','Waterproof Mascara - Jet Black',1499,'USD',4.6,412,'https://picsum.photos/seed/BEA-EYES-002/600/600','Volumizing waterproof mascara that lasts.','Smudge-resistant formula that lifts and separates lashes for a bold look.','{"color":"Jet Black"}','in_stock'),
  ('40000000-0000-0000-0000-000000000003','BEA-LIPS-003','Matte Lipstick - Rosewood',1299,'USD',4.3,256,'https://picsum.photos/seed/BEA-LIPS-003/600/600','Comfortable matte lipstick with rich pigment.','Creamy matte lipstick that glides on smoothly and sets to a soft matte finish.','{"shade":"Rosewood"}','in_stock'),
  ('40000000-0000-0000-0000-000000000004','BEA-BRUS-004','Makeup Brush Set (10-Piece)',2199,'USD',4.5,89,'https://picsum.photos/seed/BEA-BRUS-004/600/600','Soft synthetic brushes for face and eyes.','A complete brush set for everyday makeup looks. Includes case for travel.','{"pieces":10}','in_stock'),
  ('40000000-0000-0000-0000-000000000005','BEA-CLEA-005','Gentle Facial Cleanser (8 oz)',1199,'USD',4.7,501,'https://picsum.photos/seed/BEA-CLEA-005/600/600','Non-stripping daily cleanser.','A gentle cleanser that removes dirt and makeup while keeping skin balanced.','{"size":"8oz"}','in_stock'),
  ('40000000-0000-0000-0000-000000000006','BEA-MOIS-006','Daily Moisturizer with Hyaluronic Acid',1899,'USD',4.6,342,'https://picsum.photos/seed/BEA-MOIS-006/600/600','Hydration for all skin types.','Lightweight moisturizer with hyaluronic acid for long-lasting hydration.','{"keyIngredient":"Hyaluronic Acid"}','in_stock'),
  ('40000000-0000-0000-0000-000000000007','BEA-SUNS-007','Mineral Sunscreen SPF 50',1999,'USD',4.2,210,'https://picsum.photos/seed/BEA-SUNS-007/600/600','Broad spectrum mineral protection.','Mineral sunscreen with zinc oxide. Leaves minimal white cast and layers well under makeup.','{"spf":50}','in_stock'),
  ('40000000-0000-0000-0000-000000000008','BEA-SERU-008','Vitamin C Brightening Serum',2499,'USD',4.5,178,'https://picsum.photos/seed/BEA-SERU-008/600/600','Brightens and evens skin tone.','A vitamin C serum formulated to reduce dullness and improve the look of uneven tone over time.','{"active":"Vitamin C"}','in_stock'),
  ('40000000-0000-0000-0000-000000000009','BEA-SHAM-009','Clarifying Shampoo',1399,'USD',4.1,67,'https://picsum.photos/seed/BEA-SHAM-009/600/600','Deep clean without stripping.','Clarifying shampoo that removes buildup and restores shine.','{"hairType":"All"}','in_stock'),
  ('40000000-0000-0000-0000-000000000010','BEA-COND-010','Moisture Conditioner',1499,'USD',4.4,73,'https://picsum.photos/seed/BEA-COND-010/600/600','Smooth, soft hair in minutes.','A moisture-rich conditioner that detangles and softens hair.','{"hairType":"Dry"}','in_stock'),

  ('40000000-0000-0000-0000-000000000011','SPO-YOGA-011','Non-Slip Yoga Mat (6mm)',2499,'USD',4.7,980,'https://picsum.photos/seed/SPO-YOGA-011/600/600','Cushioned, grippy yoga mat for daily practice.','Durable non-slip yoga mat with 6mm thickness for comfort and stability.','{"thickness_mm":6}','in_stock'),
  ('40000000-0000-0000-0000-000000000012','SPO-WEIG-012','Adjustable Dumbbells (Pair)',12999,'USD',4.6,322,'https://picsum.photos/seed/SPO-WEIG-012/600/600','Space-saving adjustable weights.','Adjustable dumbbells with quick-change dial system for home workouts.','{"maxWeight":"50lb"}','low_stock'),
  ('40000000-0000-0000-0000-000000000013','SPO-CARD-013','Jump Rope - Speed Cable',999,'USD',4.3,141,'https://picsum.photos/seed/SPO-CARD-013/600/600','Fast, smooth jump rope for cardio.','Lightweight speed rope with adjustable length and comfortable handles.','{"length":"adjustable"}','in_stock'),
  ('40000000-0000-0000-0000-000000000014','SPO-RECO-014','Foam Roller - High Density',1799,'USD',4.5,402,'https://picsum.photos/seed/SPO-RECO-014/600/600','Recovery tool for sore muscles.','High-density foam roller for post-workout recovery and mobility work.','{"density":"high"}','in_stock'),
  ('40000000-0000-0000-0000-000000000015','SPO-TENT-015','2-Person Backpacking Tent',8999,'USD',4.4,87,'https://picsum.photos/seed/SPO-TENT-015/600/600','Lightweight tent for weekend trips.','A compact 2-person tent with rainfly and easy setup—great for hiking and camping.','{"capacity":2}','in_stock'),

  ('40000000-0000-0000-0000-000000000016','CLO-WTOP-016','Women''s Everyday Tee',1599,'USD',4.2,55,'https://picsum.photos/seed/CLO-WTOP-016/600/600','Soft cotton tee with classic fit.','An everyday t-shirt that pairs with anything. Breathable and comfortable.','{"size":"M","color":"White"}','in_stock'),
  ('40000000-0000-0000-0000-000000000017','CLO-WDRS-017','Women''s Midi Dress - Floral',4599,'USD',4.6,33,'https://picsum.photos/seed/CLO-WDRS-017/600/600','Flowy midi dress with floral print.','A flattering midi dress with a lightweight fabric and easy fit for day-to-night.','{"size":"S","pattern":"Floral"}','in_stock'),
  ('40000000-0000-0000-0000-000000000018','CLO-MSHI-018','Men''s Button-Down Shirt',3499,'USD',4.4,61,'https://picsum.photos/seed/CLO-MSHI-018/600/600','Crisp button-down for work or casual.','A versatile button-down shirt with a modern cut and comfortable fabric.','{"size":"L","color":"Blue"}','in_stock'),
  ('40000000-0000-0000-0000-000000000019','CLO-SNEA-019','Classic Sneakers',5999,'USD',4.5,204,'https://picsum.photos/seed/CLO-SNEA-019/600/600','Comfortable everyday sneakers.','Classic sneakers with cushioned insole and durable outsole for daily wear.','{"size":"10"}','in_stock'),
  ('40000000-0000-0000-0000-000000000020','CLO-RING-020','Sterling Silver Band Ring',2999,'USD',4.7,18,'https://picsum.photos/seed/CLO-RING-020/600/600','Minimal sterling silver ring.','A polished sterling silver band ring—simple, timeless, and easy to stack.','{"material":"Sterling Silver"}','in_stock'),

  ('40000000-0000-0000-0000-000000000021','HOM-COOK-021','Nonstick Fry Pan (10-inch)',2899,'USD',4.5,310,'https://picsum.photos/seed/HOM-COOK-021/600/600','Even heating nonstick pan.','A 10-inch nonstick fry pan for eggs, veggies, and quick dinners. Dishwasher safe.','{"diameter_in":10}','in_stock'),
  ('40000000-0000-0000-0000-000000000022','HOM-COFF-022','Electric Kettle - 1.7L',3499,'USD',4.6,222,'https://picsum.photos/seed/HOM-COFF-022/600/600','Fast boiling electric kettle.','Stainless steel electric kettle with auto shut-off and boil-dry protection.','{"capacity_l":1.7}','in_stock'),
  ('40000000-0000-0000-0000-000000000023','HOM-TABL-023','Stoneware Dinnerware Set (16-Piece)',7999,'USD',4.4,74,'https://picsum.photos/seed/HOM-TABL-023/600/600','Modern stoneware for everyday meals.','A 16-piece stoneware dinnerware set that''s microwave and dishwasher safe.','{"pieces":16}','in_stock'),
  ('40000000-0000-0000-0000-000000000024','HOM-LAMP-024','LED Table Lamp - Warm White',2599,'USD',4.1,48,'https://picsum.photos/seed/HOM-LAMP-024/600/600','Warm light for desk or nightstand.','Compact LED table lamp with warm white glow and touch control.','{"colorTemp":"Warm"}','in_stock'),
  ('40000000-0000-0000-0000-000000000025','OFF-PENS-025','Gel Pens (12-Pack)',1299,'USD',4.6,190,'https://picsum.photos/seed/OFF-PENS-025/600/600','Smooth-writing gel pens in assorted colors.','A 12-pack of gel pens with vivid ink and comfortable grip for everyday writing.','{"count":12}','in_stock'),

  ('40000000-0000-0000-0000-000000000026','OFF-NOTE-026','Hardcover Notebook - Dotted',1699,'USD',4.5,92,'https://picsum.photos/seed/OFF-NOTE-026/600/600','Dotted pages for bullet journaling.','A durable hardcover notebook with dotted pages, ribbon bookmark, and elastic closure.','{"pages":192}','in_stock'),
  ('40000000-0000-0000-0000-000000000027','TOO-DRIL-027','Cordless Drill/Driver Kit',8999,'USD',4.7,511,'https://picsum.photos/seed/TOO-DRIL-027/600/600','Reliable drill for home projects.','Cordless drill/driver kit with battery, charger, and bit set. Great for DIY tasks.','{"voltage":"18V"}','in_stock'),
  ('40000000-0000-0000-0000-000000000028','TOO-SCRE-028','Precision Screwdriver Set',1999,'USD',4.4,133,'https://picsum.photos/seed/TOO-SCRE-028/600/600','Small screwdrivers for electronics.','Precision screwdriver set with multiple bits for phones, laptops, and gadgets.','{"bits":24}','in_stock'),
  ('40000000-0000-0000-0000-000000000029','TOO-BULB-029','Smart LED Bulb (2-Pack)',2499,'USD',4.2,205,'https://picsum.photos/seed/TOO-BULB-029/600/600','App-controlled smart bulbs.','Smart LED bulbs with adjustable brightness and schedules. Works with common voice assistants.','{"count":2}','in_stock'),

  ('40000000-0000-0000-0000-000000000030','HEA-MULT-030','Daily Multivitamin Gummies',1599,'USD',4.3,88,'https://picsum.photos/seed/HEA-MULT-030/600/600','Tasty daily vitamins.','Daily multivitamin gummies with essential nutrients.','{"servings":60}','in_stock'),
  ('40000000-0000-0000-0000-000000000031','HEA-ORAL-031','Electric Toothbrush - Starter',3999,'USD',4.5,144,'https://picsum.photos/seed/HEA-ORAL-031/600/600','Rechargeable electric toothbrush.','Electric toothbrush with 2-minute timer and soft bristles for a gentle clean.','{"modes":2}','in_stock'),
  ('40000000-0000-0000-0000-000000000032','HEA-CLEA-032','All-Purpose Cleaner (32 oz)',599,'USD',4.4,77,'https://picsum.photos/seed/HEA-CLEA-032/600/600','Fresh-scent multi-surface cleaner.','All-purpose cleaner for kitchen, bathroom, and everyday messes.','{"size":"32oz"}','in_stock'),

  ('40000000-0000-0000-0000-000000000033','GAR-LITE-033','Solar Pathway Lights (8-Pack)',2999,'USD',4.1,65,'https://picsum.photos/seed/GAR-LITE-033/600/600','Easy solar lights for walkways.','Set of 8 solar pathway lights with dusk-to-dawn operation and weather resistance.','{"count":8}','in_stock'),
  ('40000000-0000-0000-0000-000000000034','GAR-GRIL-034','Charcoal Grill - 18-inch',6999,'USD',4.2,41,'https://picsum.photos/seed/GAR-GRIL-034/600/600','Classic charcoal grill for backyard cooking.','18-inch charcoal grill with adjustable vents and ash catcher.','{"diameter_in":18}','in_stock'),
  ('40000000-0000-0000-0000-000000000035','GAR-SOIL-035','Organic Potting Soil (20 qt)',1299,'USD',4.6,112,'https://picsum.photos/seed/GAR-SOIL-035/600/600','Nutrient-rich potting soil.','Organic potting soil blend for indoor and outdoor container plants.','{"volume":"20qt"}','in_stock'),

  ('40000000-0000-0000-0000-000000000036','ELE-LAPT-036','14-inch Laptop - 8GB RAM, 256GB SSD',49999,'USD',4.4,291,'https://picsum.photos/seed/ELE-LAPT-036/600/600','Everyday laptop for work and school.','A lightweight 14-inch laptop with fast SSD storage and reliable performance for daily tasks.','{"ram":"8GB","storage":"256GB"}','in_stock'),
  ('40000000-0000-0000-0000-000000000037','ELE-MONI-037','27-inch IPS Monitor',18999,'USD',4.6,180,'https://picsum.photos/seed/ELE-MONI-037/600/600','Crisp 27-inch IPS display.','27-inch IPS monitor with vibrant color and slim bezels—great for productivity.','{"size_in":27}','in_stock'),
  ('40000000-0000-0000-0000-000000000038','ELE-HEAD-038','Wireless Noise-Canceling Headphones',12999,'USD',4.7,623,'https://picsum.photos/seed/ELE-HEAD-038/600/600','Immersive sound with ANC.','Wireless headphones with active noise cancellation and long battery life for travel and work.','{"batteryHours":30}','in_stock'),
  ('40000000-0000-0000-0000-000000000039','ELE-CAME-039','Mirrorless Camera Body',69999,'USD',4.5,54,'https://picsum.photos/seed/ELE-CAME-039/600/600','Compact mirrorless camera for creators.','High-resolution mirrorless camera body with fast autofocus and 4K video.','{"sensor":"APS-C"}','low_stock'),

  ('40000000-0000-0000-0000-000000000040','PHO-ANDR-040','Android Smartphone - 128GB',29999,'USD',4.3,211,'https://picsum.photos/seed/PHO-ANDR-040/600/600','Fast Android phone with great camera.','Unlocked Android smartphone with 128GB storage and a bright display.','{"storage":"128GB"}','in_stock'),
  ('40000000-0000-0000-0000-000000000041','PHO-IOS-041','iOS Smartphone - 128GB',59999,'USD',4.6,402,'https://picsum.photos/seed/PHO-IOS-041/600/600','Popular iOS phone with smooth performance.','Unlocked iOS smartphone with 128GB storage and excellent battery life.','{"storage":"128GB"}','in_stock'),
  ('40000000-0000-0000-0000-000000000042','PHO-CASR-042','Rugged Phone Case',1999,'USD',4.4,97,'https://picsum.photos/seed/PHO-CASR-042/600/600','Drop protection with grippy texture.','Rugged protective case designed to absorb shock and protect your phone from drops.','{"material":"TPU"}','in_stock'),
  ('40000000-0000-0000-0000-000000000043','PHO-WIRE-043','Wireless Charger Pad - 15W',2499,'USD',4.2,158,'https://picsum.photos/seed/PHO-WIRE-043/600/600','Fast wireless charging pad.','15W wireless charger pad compatible with most Qi-enabled devices.','{"watt":15}','in_stock'),

  ('40000000-0000-0000-0000-000000000044','GAM-PS5-044','Next-Gen Console - PlayStation Edition',49999,'USD',4.8,1001,'https://picsum.photos/seed/GAM-PS5-044/600/600','Next-gen gaming console experience.','A next-gen console delivering fast load times and stunning visuals.','{"platform":"PlayStation"}','out_of_stock'),
  ('40000000-0000-0000-0000-000000000045','GAM-XBX-045','Next-Gen Console - Xbox Edition',49999,'USD',4.7,812,'https://picsum.photos/seed/GAM-XBX-045/600/600','Powerful console for modern gaming.','A next-gen console with high performance and a large game library.','{"platform":"Xbox"}','in_stock'),
  ('40000000-0000-0000-0000-000000000046','GAM-CTRL-046','Wireless Controller',5999,'USD',4.6,420,'https://picsum.photos/seed/GAM-CTRL-046/600/600','Responsive wireless controller.','Wireless controller with ergonomic grip and low-latency input.','{"color":"Black"}','in_stock'),
  ('40000000-0000-0000-0000-000000000047','GAM-RPG-047','Fantasy RPG Game (Console)',6999,'USD',4.5,201,'https://picsum.photos/seed/GAM-RPG-047/600/600','Epic open-world RPG adventure.','Explore a vast world, customize your character, and complete quests in this fantasy RPG.','{"genre":"RPG"}','in_stock'),

  ('40000000-0000-0000-0000-000000000048','GRO-SPAR-048','Sparkling Water Variety Pack (12)',1099,'USD',4.3,66,'https://picsum.photos/seed/GRO-SPAR-048/600/600','Refreshing sparkling water pack.','A variety pack of sparkling waters with crisp flavors and zero sugar.','{"count":12}','in_stock'),
  ('40000000-0000-0000-0000-000000000049','GRO-CHIP-049','Kettle Cooked Chips - Sea Salt',499,'USD',4.4,120,'https://picsum.photos/seed/GRO-CHIP-049/600/600','Crunchy kettle chips with sea salt.','Kettle cooked chips with a satisfying crunch and simple ingredients.','{"flavor":"Sea Salt"}','in_stock'),
  ('40000000-0000-0000-0000-000000000050','GRO-COFF-050','Medium Roast Coffee Beans (2 lb)',1599,'USD',4.6,98,'https://picsum.photos/seed/GRO-COFF-050/600/600','Smooth medium roast coffee.','Whole bean medium roast coffee with balanced flavor—great for drip or espresso.','{"weight":"2lb"}','in_stock'),

  -- Additional 10 products to reach 60
  ('40000000-0000-0000-0000-000000000051','SPO-HELM-051','Cycling Helmet - Road',4599,'USD',4.5,77,'https://picsum.photos/seed/SPO-HELM-051/600/600','Lightweight road helmet with ventilation.','Road cycling helmet with adjustable fit system and excellent airflow.','{"size":"M"}','in_stock'),
  ('40000000-0000-0000-0000-000000000052','SPO-LITE-052','Bike Light Set - Front/Rear',2599,'USD',4.4,143,'https://picsum.photos/seed/SPO-LITE-052/600/600','Be seen with bright bike lights.','USB rechargeable bike light set with multiple modes for commuting.','{"rechargeable":true}','in_stock'),
  ('40000000-0000-0000-0000-000000000053','HOM-SHEE-053','Microfiber Sheet Set - Queen',3299,'USD',4.2,58,'https://picsum.photos/seed/HOM-SHEE-053/600/600','Soft microfiber sheets for everyday comfort.','Breathable microfiber sheet set with deep pockets for queen mattresses.','{"size":"Queen"}','in_stock'),
  ('40000000-0000-0000-0000-000000000054','HOM-CAND-054','Scented Candle - Vanilla',1299,'USD',4.3,39,'https://picsum.photos/seed/HOM-CAND-054/600/600','Warm vanilla scent for cozy spaces.','Scented candle with clean burn and long-lasting fragrance.','{"scent":"Vanilla"}','in_stock'),
  ('40000000-0000-0000-0000-000000000055','OFF-ORGA-055','Desk Organizer Tray',1599,'USD',4.1,27,'https://picsum.photos/seed/OFF-ORGA-055/600/600','Keep your desk tidy.','Modular desk organizer tray for pens, clips, and small accessories.','{"material":"ABS"}','in_stock'),
  ('40000000-0000-0000-0000-000000000056','TOO-HAMM-056','16oz Claw Hammer',1499,'USD',4.6,88,'https://picsum.photos/seed/TOO-HAMM-056/600/600','Classic claw hammer for DIY.','Durable 16oz claw hammer with comfortable grip for home improvement projects.','{"weight_oz":16}','in_stock'),
  ('40000000-0000-0000-0000-000000000057','HEA-PROT-057','Whey Protein Powder - Vanilla',3599,'USD',4.4,102,'https://picsum.photos/seed/HEA-PROT-057/600/600','Protein support for workouts.','Whey protein powder with vanilla flavor—mixes smoothly in shakes.','{"servings":25}','in_stock'),
  ('40000000-0000-0000-0000-000000000058','GAR-PLAN-058','Ceramic Planter Pot - 8 inch',2199,'USD',4.5,26,'https://picsum.photos/seed/GAR-PLAN-058/600/600','Modern planter for indoor plants.','Ceramic planter pot with drainage hole for healthy roots.','{"size_in":8}','in_stock'),
  ('40000000-0000-0000-0000-000000000059','ELE-SOUN-059','Soundbar with Bluetooth',9999,'USD',4.3,84,'https://picsum.photos/seed/ELE-SOUN-059/600/600','Upgrade TV audio easily.','Compact soundbar with Bluetooth streaming and clear dialogue enhancement.','{"bluetooth":true}','in_stock'),
  ('40000000-0000-0000-0000-000000000060','PHO-CABL-060','USB-C Cable (2-Pack)',999,'USD',4.6,310,'https://picsum.photos/seed/PHO-CABL-060/600/600','Durable braided USB-C cables.','Two-pack of braided USB-C cables for fast charging and data transfer.','{"count":2}','in_stock')
ON CONFLICT (id) DO NOTHING;

-- product_category mapping (each product assigned to a level-3 leaf)
INSERT INTO product_category (product_id, category_id) VALUES
  ('40000000-0000-0000-0000-000000000001','21100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000002','21100000-0000-0000-0000-000000000002'),
  ('40000000-0000-0000-0000-000000000003','21100000-0000-0000-0000-000000000003'),
  ('40000000-0000-0000-0000-000000000004','21100000-0000-0000-0000-000000000004'),
  ('40000000-0000-0000-0000-000000000005','21100000-0000-0000-0000-000000000005'),
  ('40000000-0000-0000-0000-000000000006','21100000-0000-0000-0000-000000000006'),
  ('40000000-0000-0000-0000-000000000007','21100000-0000-0000-0000-000000000007'),
  ('40000000-0000-0000-0000-000000000008','21100000-0000-0000-0000-000000000008'),
  ('40000000-0000-0000-0000-000000000009','21100000-0000-0000-0000-000000000009'),
  ('40000000-0000-0000-0000-000000000010','21100000-0000-0000-0000-000000000010'),

  ('40000000-0000-0000-0000-000000000011','22100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000012','22100000-0000-0000-0000-000000000002'),
  ('40000000-0000-0000-0000-000000000013','22100000-0000-0000-0000-000000000003'),
  ('40000000-0000-0000-0000-000000000014','22100000-0000-0000-0000-000000000004'),
  ('40000000-0000-0000-0000-000000000015','22100000-0000-0000-0000-000000000005'),

  ('40000000-0000-0000-0000-000000000016','23100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000017','23100000-0000-0000-0000-000000000002'),
  ('40000000-0000-0000-0000-000000000018','23100000-0000-0000-0000-000000000005'),
  ('40000000-0000-0000-0000-000000000019','23100000-0000-0000-0000-000000000009'),
  ('40000000-0000-0000-0000-000000000020','23100000-0000-0000-0000-000000000016'),

  ('40000000-0000-0000-0000-000000000021','24100000-0000-0000-0000-000000000005'),
  ('40000000-0000-0000-0000-000000000022','24100000-0000-0000-0000-000000000006'),
  ('40000000-0000-0000-0000-000000000023','24100000-0000-0000-0000-000000000008'),
  ('40000000-0000-0000-0000-000000000024','24100000-0000-0000-0000-000000000015'),

  ('40000000-0000-0000-0000-000000000025','25100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000026','25100000-0000-0000-0000-000000000005'),

  ('40000000-0000-0000-0000-000000000027','26100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000028','26100000-0000-0000-0000-000000000006'),
  ('40000000-0000-0000-0000-000000000029','26100000-0000-0000-0000-000000000016'),

  ('40000000-0000-0000-0000-000000000030','27100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000031','27100000-0000-0000-0000-000000000005'),
  ('40000000-0000-0000-0000-000000000032','27100000-0000-0000-0000-000000000010'),

  ('40000000-0000-0000-0000-000000000033','28100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000034','28100000-0000-0000-0000-000000000005'),
  ('40000000-0000-0000-0000-000000000035','28100000-0000-0000-0000-000000000010'),

  ('40000000-0000-0000-0000-000000000036','29100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000037','29100000-0000-0000-0000-000000000003'),
  ('40000000-0000-0000-0000-000000000038','29100000-0000-0000-0000-000000000009'),
  ('40000000-0000-0000-0000-000000000039','29100000-0000-0000-0000-000000000013'),

  ('40000000-0000-0000-0000-000000000040','30100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000041','30100000-0000-0000-0000-000000000002'),
  ('40000000-0000-0000-0000-000000000042','30100000-0000-0000-0000-000000000005'),
  ('40000000-0000-0000-0000-000000000043','30100000-0000-0000-0000-000000000010'),

  ('40000000-0000-0000-0000-000000000044','31100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000045','31100000-0000-0000-0000-000000000002'),
  ('40000000-0000-0000-0000-000000000046','31100000-0000-0000-0000-000000000005'),
  ('40000000-0000-0000-0000-000000000047','31100000-0000-0000-0000-000000000010'),

  ('40000000-0000-0000-0000-000000000048','32100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000049','32100000-0000-0000-0000-000000000005'),
  ('40000000-0000-0000-0000-000000000050','32100000-0000-0000-0000-000000000009'),

  ('40000000-0000-0000-0000-000000000051','22100000-0000-0000-0000-000000000009'),
  ('40000000-0000-0000-0000-000000000052','22100000-0000-0000-0000-000000000010'),
  ('40000000-0000-0000-0000-000000000053','24100000-0000-0000-0000-000000000001'),
  ('40000000-0000-0000-0000-000000000054','24100000-0000-0000-0000-000000000016'),
  ('40000000-0000-0000-0000-000000000055','25100000-0000-0000-0000-000000000009'),
  ('40000000-0000-0000-0000-000000000056','26100000-0000-0000-0000-000000000008'),
  ('40000000-0000-0000-0000-000000000057','27100000-0000-0000-0000-000000000002'),
  ('40000000-0000-0000-0000-000000000058','28100000-0000-0000-0000-000000000002'),
  ('40000000-0000-0000-0000-000000000059','29100000-0000-0000-0000-000000000007'),
  ('40000000-0000-0000-0000-000000000060','30100000-0000-0000-0000-000000000012')
ON CONFLICT DO NOTHING;

-- =========================
-- Denormalized category_path on product
-- =========================
-- Compute a stable path from the category tree: level1/level2/level3 (slugs)
WITH RECURSIVE cat_path AS (
  SELECT
    c.id,
    c.parent_id,
    c.slug,
    c.slug::text AS path
  FROM category c
  WHERE c.parent_id IS NULL
  UNION ALL
  SELECT
    c.id,
    c.parent_id,
    c.slug,
    (cp.path || '/' || c.slug)::text AS path
  FROM category c
  JOIN cat_path cp ON cp.id = c.parent_id
),
product_leaf AS (
  SELECT pc.product_id, cp.path
  FROM product_category pc
  JOIN cat_path cp ON cp.id = pc.category_id
)
UPDATE product p
SET category_path = pl.path
FROM product_leaf pl
WHERE p.id = pl.product_id;


-- =========================
-- Wishlist (non-empty for demo user)
-- =========================

INSERT INTO wishlist_item (user_id, product_id)
VALUES
  ('00000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000011'),
  ('00000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000036'),
  ('00000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000038'),
  ('00000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000045'),
  ('00000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000021'),
  ('00000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000027'),
  ('00000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000050')
ON CONFLICT DO NOTHING;

-- =========================
-- Orders (3-5 recent orders for demo user)
-- =========================

INSERT INTO "order" (id, user_id, order_number, created_at, ship_to_name, status, currency, total_cents)
VALUES
  ('50000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002','100000001', '2025-01-03T10:00:00Z'::timestamptz,'Dana Demo','delivered','USD',  4295),
  ('50000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000002','100000002', '2025-01-08T10:00:00Z'::timestamptz,'Dana Demo','shipped','USD',     9999),
  ('50000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000002','100000003', '2025-01-12T10:00:00Z'::timestamptz,'Dana Demo','processing','USD',  15996),
  ('50000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000002','100000004', '2024-12-21T10:00:00Z'::timestamptz,'Dana Demo','delivered','USD',  12999)
ON CONFLICT (id) DO NOTHING;

-- Order 100000001: 3 items
INSERT INTO order_item (id, order_id, product_id, sku, name, unit_price_cents, quantity, line_total_cents)
VALUES
  ('51000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000025','OFF-PENS-025','Gel Pens (12-Pack)',1299,1,1299),
  ('51000000-0000-0000-0000-000000000002','50000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000049','GRO-CHIP-049','Kettle Cooked Chips - Sea Salt',499,2,998),
  ('51000000-0000-0000-0000-000000000003','50000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000013','SPO-CARD-013','Jump Rope - Speed Cable',999,2,1998)
ON CONFLICT (id) DO NOTHING;

-- Order 100000002: 1 item
INSERT INTO order_item (id, order_id, product_id, sku, name, unit_price_cents, quantity, line_total_cents)
VALUES
  ('51000000-0000-0000-0000-000000000004','50000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000059','ELE-SOUN-059','Soundbar with Bluetooth',9999,1,9999)
ON CONFLICT (id) DO NOTHING;

-- Order 100000003: 2 items
INSERT INTO order_item (id, order_id, product_id, sku, name, unit_price_cents, quantity, line_total_cents)
VALUES
  ('51000000-0000-0000-0000-000000000005','50000000-0000-0000-0000-000000000003','40000000-0000-0000-0000-000000000038','ELE-HEAD-038','Wireless Noise-Canceling Headphones',12999,1,12999),
  ('51000000-0000-0000-0000-000000000006','50000000-0000-0000-0000-000000000003','40000000-0000-0000-0000-000000000060','PHO-CABL-060','USB-C Cable (2-Pack)',999,3,2997)
ON CONFLICT (id) DO NOTHING;

-- Order 100000004: 1 item
INSERT INTO order_item (id, order_id, product_id, sku, name, unit_price_cents, quantity, line_total_cents)
VALUES
  ('51000000-0000-0000-0000-000000000007','50000000-0000-0000-0000-000000000004','40000000-0000-0000-0000-000000000012','SPO-WEIG-012','Adjustable Dumbbells (Pair)',12999,1,12999)
ON CONFLICT (id) DO NOTHING;

-- =========================
-- Seed sanity checks (fail fast in CI)
-- =========================

DO $$
DECLARE
  mismatch_count integer;
BEGIN
  SELECT COUNT(*)
  INTO mismatch_count
  FROM "order" o
  WHERE o.total_cents <> (
    SELECT COALESCE(SUM(oi.line_total_cents), 0)
    FROM order_item oi
    WHERE oi.order_id = o.id
  );

  IF mismatch_count <> 0 THEN
    RAISE EXCEPTION 'DATA INTEGRITY: % seeded orders have incorrect total_cents vs sum(order_item.line_total_cents)', mismatch_count;
  END IF;
END $$;


-- =========================
-- Cart (optional) - seed a small cart for demo user
-- =========================

INSERT INTO cart (id, user_id, currency)
VALUES
  ('60000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002','USD')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO cart_item (cart_id, product_id, quantity)
VALUES
  ('60000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000011',1),
  ('60000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000042',2)
ON CONFLICT DO NOTHING;

COMMIT;
