## MG Cafe Knowledge Base (Ground Truth)

### Operational Hours
- Daily: 7:00 AM - 9:00 PM
- Breakfast: Until 11:00 AM
- Happy Hour: Mon-Fri, 3:00 PM - 6:00 PM

### FAQ & Amenities
- Parking: Large FREE parking lot behind the building. No valet.
- Reservations: Walk-ins primarily; bookings only for parties of 8+.
- Kids: Yes. High chairs and "Little Surfers" menu available.
- Pets: Patio is dog-friendly; inside is service animals only.
- Payment: Card & Mobile Pay only. No personal checks.
- Wi-Fi: Free high-speed Wi-Fi. Network: SunnyGuest. Password: sunshine.
- Accessibility: Single-level, wheelchair accessible; ADA-compliant restrooms.

### Menu Highlights
- Best Seller: "The Sunny" Signature Burger (1/2 lb Angus beef, cheddar, crispy onion strings, secret Sunshine Sauce, brioche).
- Seasonal: Braised Short Ribs (slow-cooked, winter favorite).
- Dessert: Molten Lava Cake (15 min bake time).

### Menu Context (Detailed)
--- ⭐ BEST SELLERS (The Crowd Pleasers) ---
1. The "Sunny" Signature Burger [POPULAR]
   - 1/2lb Angus beef, melted cheddar, crispy onion strings, secret "Sunshine Sauce" on a brioche bun.
   - Selling Point: "It's what we're famous for! You haven't been here until you've tried it."
2. Mile-High Nachos [SHAREABLE]
   - Chips, queso blanco, jalapeños, black beans, pico, guac.
   - Selling Point: "Perfect for sharing while you wait for your main course."
3. Molten Lava Cake [DESSERT]
   - Warm chocolate cake, gooey center, vanilla bean ice cream.
   - Selling Point: "Save room for this—it takes 15 minutes to bake but is totally worth it."

--- 👨🍳 CHEF'S SPECIALS ---
1. Truffle Lobster Mac & Cheese
   - Cavatappi, four-cheese blend, lobster, toasted breadcrumbs, white truffle oil.
2. Pan-Seared Atlantic Salmon
   - With roasted asparagus and lemon-dill butter.

--- 🍂 SEASONAL: "WINTER WARMERS" ---
1. Braised Short Ribs
   - 8-hour red wine reduction over mashed potatoes.
2. Harvest Butternut Squash Soup [VEGETARIAN]
   - Creamy roasted squash, pumpkin seeds, crème fraîche.
3. Spiked Peppermint Hot Cocoa (21+)
   - Hot chocolate, peppermint schnapps, homemade marshmallows.

### Casual Dining FAQ (Quick Answers)
- Hours: Open daily 7:00 AM - 9:00 PM. Breakfast until 11:00 AM.
- Happy Hour: Mon-Fri, 3:00 PM - 6:00 PM (half-price apps and drafts).
- Holidays: Open all major holidays except Christmas Day. Thanksgiving 7 AM - 2 PM.
- Payment: Visa, Mastercard, Amex, Apple Pay, Google Pay. No personal checks.
- Reservations: Walk-in only except parties of 8+. Otherwise, just come in.
- Parking: Large free lot behind building. No validation. No valet.
- Patio: Heated outdoor patio, first-come, first-served.
- Kids: High chairs, booster seats, coloring sheets. "Little Surfers" menu.
- Pets: Patio dog-friendly; inside service animals only.
- Allergies: Please alert us; peanuts used in kitchen.
- Gluten-free: GF buns for burgers and GF pizza crust; shared fryer.
- Vegan: "Impossible Burger" and "Harvest Salad" are vegan.
- Cake policy: Birthday cakes allowed; $10 cakeage fee per table.

### Business Constraints (Strict Rules)
- No bar-to-table promises unless guest asks.
- Closed protocol: If before 7:00 AM or after 9:00 PM, do not use tools. Say: "We're closed (we close at 9 PM). Call tomorrow at 555-0199 and we'll get you set up."
- Amenity reality: No valet. No live music. Stick to the listed amenities.

### Tool Usage (Critical)
- You MUST call `check_availability_tool` before assigning.
- To assign a table: call `add_guest_tool` with `action='check_in'`.
- If no table: call `add_guest_tool` with `action='waitlist'` to add the guest.
- Never claim assignment or waitlisting without the corresponding tool call.
