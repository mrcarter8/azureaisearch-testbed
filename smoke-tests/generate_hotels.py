"""Generate 100 semantically rich hotel documents for the hotels index schema."""
import json
import random

random.seed(42)

# --- Data pools ---
categories = [
    "Luxury", "Boutique", "Resort and Spa", "Budget",
    "Extended-Stay", "Business", "Historic", "Eco-Friendly",
]

cities_data = [
    ("New York", "NY", "10001", "USA", -73.9857, 40.7484),
    ("San Francisco", "CA", "94102", "USA", -122.4194, 37.7749),
    ("Chicago", "IL", "60601", "USA", -87.6298, 41.8781),
    ("Miami", "FL", "33101", "USA", -80.1918, 25.7617),
    ("Seattle", "WA", "98101", "USA", -122.3321, 47.6062),
    ("Austin", "TX", "73301", "USA", -97.7431, 30.2672),
    ("Nashville", "TN", "37201", "USA", -86.7816, 36.1627),
    ("Denver", "CO", "80201", "USA", -104.9903, 39.7392),
    ("Boston", "MA", "02101", "USA", -71.0589, 42.3601),
    ("Portland", "OR", "97201", "USA", -122.6765, 45.5152),
    ("New Orleans", "LA", "70112", "USA", -90.0715, 29.9511),
    ("San Diego", "CA", "92101", "USA", -117.1611, 32.7157),
    ("Savannah", "GA", "31401", "USA", -81.0998, 32.0809),
    ("Scottsdale", "AZ", "85251", "USA", -111.9261, 33.4942),
    ("Honolulu", "HI", "96801", "USA", -157.8583, 21.3069),
    ("Charleston", "SC", "29401", "USA", -79.9311, 32.7765),
    ("Aspen", "CO", "81611", "USA", -106.8175, 39.1911),
    ("Las Vegas", "NV", "89101", "USA", -115.1398, 36.1699),
    ("Orlando", "FL", "32801", "USA", -81.3792, 28.5383),
    ("Washington", "DC", "20001", "USA", -77.0369, 38.9072),
]

hotel_names_templates = [
    "The {adj} {noun}",
    "{city} {type} Hotel",
    "Hotel {adj}",
    "{noun} {type}",
    "The {city} {noun}",
    "{adj} {type} & Suites",
    "Grand {noun} Hotel",
    "The {noun} at {city}",
    "{city} {adj} Resort",
    "{adj} {noun} Inn",
]

adjectives = [
    "Grand", "Royal", "Azure", "Golden", "Silver", "Crimson", "Emerald",
    "Sapphire", "Pearl", "Ivory", "Majestic", "Noble", "Serene", "Radiant",
    "Tranquil", "Pristine", "Summit", "Harbor", "Coastal", "Highland",
]

nouns = [
    "Palace", "Plaza", "Pinnacle", "Meridian", "Oasis", "Citadel", "Haven",
    "Crest", "Vista", "Terrace", "Lighthouse", "Promenade", "Observatory",
    "Canopy", "Atrium", "Quarters", "Retreat", "Residence", "Lodge", "Manor",
]

types = ["Boutique", "Resort", "Suites", "Inn", "Hotel", "Lodge", "Residence"]

room_types = [
    ("Standard Room", "1 Queen Bed", 2),
    ("Deluxe Room", "1 King Bed", 2),
    ("Suite", "1 King Bed", 3),
    ("Double Room", "2 Queen Beds", 4),
    ("Family Suite", "2 Queen Beds", 5),
    ("Executive Suite", "1 King Bed", 2),
    ("Penthouse Suite", "1 King Bed", 2),
    ("Studio Room", "1 Queen Bed", 2),
    ("Budget Room", "1 Full Bed", 2),
    ("Presidential Suite", "1 King Bed", 4),
]

tag_pool = [
    "pool", "spa", "gym", "restaurant", "bar", "concierge", "room service",
    "free wifi", "business center", "valet parking", "rooftop terrace",
    "pet friendly", "kids club", "airport shuttle", "ocean view",
    "mountain view", "city view", "garden", "laundry service",
    "continental breakfast", "all-inclusive", "beachfront", "ski-in/ski-out",
    "wellness center", "meeting rooms", "ev charging", "bicycle rental",
    "tennis court", "golf course", "sauna",
]

room_tag_pool = [
    "coffee maker", "tv", "minibar", "safe", "balcony", "bathrobe", "desk",
    "iron", "hair dryer", "jacuzzi tub", "fireplace", "kitchenette",
    "sofa bed", "rainfall shower", "smart tv", "bluetooth speaker",
    "nespresso machine", "suite", "bathroom shower", "bidet",
]

views = [
    "skyline", "ocean", "mountain", "garden", "river",
    "lake", "harbor", "park", "cityscape", "valley",
]

years_historic = [
    "1870", "1885", "1890", "1901", "1905",
    "1912", "1922", "1929", "1938", "1945",
]

streets = [
    "Main St", "Broadway", "Market St", "Oak Ave", "Park Blvd",
    "Riverside Dr", "Elm St", "Harbor Way", "Pine St", "Maple Ave",
    "Ocean Blvd", "Sunset Dr", "Lakeview Rd", "Mountain Pass", "Canyon Rd",
    "Promenade Walk", "Heritage Ln", "Garden Path", "Commerce St", "University Ave",
]

renovation_years = list(range(2010, 2026))

# Description templates keyed by category — semantically rich for search relevance
desc_templates = {
    "Luxury": [
        (
            "An opulent {n}-star retreat in the heart of {city}, featuring world-class "
            "dining, a full-service spa, and breathtaking {view} views. Guests enjoy "
            "marble-clad suites, a Michelin-starred restaurant, and personalized butler "
            "service. Perfect for discerning travelers who expect nothing but the finest "
            "accommodations."
        ),
        (
            "Experience unparalleled elegance at this iconic {city} luxury hotel. From "
            "the crystal chandeliers in the grand lobby to the hand-crafted furnishings "
            "in every room, every detail speaks to refined taste. The rooftop infinity "
            "pool overlooks the glittering skyline while the concierge team curates "
            "bespoke city experiences."
        ),
    ],
    "Boutique": [
        (
            "A one-of-a-kind boutique hotel in {city} that blends contemporary art with "
            "intimate comfort. Each of the {rooms} individually designed rooms tells a "
            "unique story through local artwork and artisan furniture. The on-site cafe "
            "serves farm-to-table cuisine sourced from nearby purveyors."
        ),
        (
            "Tucked away on a charming {city} side street, this intimate boutique hotel "
            "offers a curated escape from the ordinary. With only {rooms} rooms, guests "
            "receive personalized attention from a staff that anticipates every need. "
            "The rooftop garden bar is a hidden gem among locals and travelers alike."
        ),
    ],
    "Resort and Spa": [
        (
            "An award-winning resort and spa destination in {city} offering complete "
            "rejuvenation. Spread across lush tropical grounds, the property features a "
            "championship golf course, six swimming pools, and a world-renowned wellness "
            "center with over forty treatment rooms. All-day dining options range from "
            "casual poolside fare to elegant tasting menus."
        ),
        (
            "Escape to paradise at this stunning {city} resort where relaxation meets "
            "adventure. Guests unwind at the oceanfront spa while thrill-seekers enjoy "
            "water sports, zipline tours, and guided nature hikes. The resort culinary "
            "program features cooking classes with the executive chef using locally "
            "harvested ingredients."
        ),
    ],
    "Budget": [
        (
            "A smart-value hotel in {city} that proves comfort does not require a "
            "premium price. Clean, modern rooms feature pillow-top mattresses, "
            "high-speed wifi, and a functional workspace. The complimentary breakfast "
            "buffet and 24-hour coffee station keep guests fueled for exploration, and "
            "the central location puts major attractions within walking distance."
        ),
        (
            "Ideal for budget-conscious travelers visiting {city}, this no-frills hotel "
            "delivers on the essentials: spotless rooms, reliable wifi, and a friendly "
            "front desk team available around the clock. The on-site self-service "
            "laundry and free parking make extended stays painless."
        ),
    ],
    "Extended-Stay": [
        (
            "Designed for guests who need more than a hotel room, this {city} "
            "extended-stay property features fully equipped kitchens, in-suite "
            "washer/dryers, and separate living areas. Weekly housekeeping, a "
            "well-stocked grocery delivery partnership, and a communal outdoor grill "
            "area make long-term stays feel like home."
        ),
        (
            "Whether relocating, on a project assignment, or simply exploring {city} at "
            "a leisurely pace, this extended-stay hotel offers apartment-style suites "
            "with full kitchens, ergonomic home offices, and generous closet space. "
            "Complimentary evening socials help guests connect with fellow long-term "
            "travelers."
        ),
    ],
    "Business": [
        (
            "A premier business hotel in downtown {city} with direct skybridge access "
            "to the convention center. Every room features dual monitors, ergonomic "
            "Herman Miller chairs, and noise-canceling panels. The executive floor "
            "lounge offers complimentary hors d'oeuvres, premium cocktails, and private "
            "meeting pods bookable by the hour."
        ),
        (
            "Engineered for the modern professional, this {city} business hotel "
            "combines productivity with comfort. High-speed fiber internet, a 24-hour "
            "business center with printing and shipping services, and same-day dry "
            "cleaning ensure nothing disrupts a tight schedule. The lobby cafe doubles "
            "as a co-working space."
        ),
    ],
    "Historic": [
        (
            "Step back in time at this lovingly restored {year} landmark in {city}. "
            "Original architectural details including crown moldings, stained glass "
            "windows, and a sweeping grand staircase coexist with modern comforts like "
            "smart room controls and rainfall showers. The on-site museum chronicles "
            "the building's storied past."
        ),
        (
            "A registered historic property in the heart of {city}'s heritage district, "
            "this hotel occupies a beautifully preserved {year} building. Period "
            "antiques furnish the common areas while guest rooms blend vintage charm "
            "with contemporary amenities. Evening ghost tours and historical walking "
            "guides depart from the ornate lobby."
        ),
    ],
    "Eco-Friendly": [
        (
            "A LEED Platinum-certified hotel in {city} that proves sustainability and "
            "luxury can coexist. Solar panels generate seventy percent of the "
            "building's energy, greywater recycling irrigates the organic rooftop "
            "garden, and every amenity is plastic-free. Guests sleep on organic cotton "
            "linens and dine on zero-waste cuisine."
        ),
        (
            "This pioneering eco-friendly hotel in {city} is built from reclaimed "
            "timber and recycled steel. The living green wall in the atrium naturally "
            "purifies indoor air, while the kitchen composts one hundred percent of "
            "food waste. Electric vehicle charging stations and a bicycle-share fleet "
            "encourage car-free exploration."
        ),
    ],
}

desc_fr_templates = {
    "Luxury": (
        "Un hotel de luxe exceptionnel au coeur de {city}, offrant un service de "
        "conciergerie personnalise, un spa de classe mondiale et une cuisine "
        "gastronomique primee."
    ),
    "Boutique": (
        "Un charmant hotel-boutique a {city} ou art contemporain et confort intime "
        "se rencontrent dans un cadre unique."
    ),
    "Resort and Spa": (
        "Un complexe hotelier et spa prime a {city} proposant des soins de "
        "bien-etre, un parcours de golf et une cuisine raffinee."
    ),
    "Budget": (
        "Un hotel economique bien situe a {city} offrant des chambres propres et "
        "modernes avec petit-dejeuner gratuit."
    ),
    "Extended-Stay": (
        "Un hotel de sejour prolonge a {city} avec des suites entierement equipees "
        "comprenant cuisine et espace de vie."
    ),
    "Business": (
        "Un hotel d'affaires de premier plan au centre-ville de {city} avec acces "
        "direct au centre de congres."
    ),
    "Historic": (
        "Un hotel historique magnifiquement restaure dans le quartier patrimonial "
        "de {city}."
    ),
    "Eco-Friendly": (
        "Un hotel ecologique certifie a {city} alliant durabilite et confort haut "
        "de gamme."
    ),
}


def generate_hotels():
    hotels = []
    used_names = set()

    for i in range(1, 101):
        cat = categories[(i - 1) % len(categories)]
        city_info = cities_data[(i - 1) % len(cities_data)]
        city, state, zipcode, country, lon, lat = city_info

        # Generate unique name
        for _ in range(100):
            tmpl = random.choice(hotel_names_templates)
            adj = random.choice(adjectives)
            noun = random.choice(nouns)
            typ = random.choice(types)
            name = tmpl.format(adj=adj, noun=noun, city=city, type=typ)
            if name not in used_names:
                used_names.add(name)
                break

        # Description
        desc = random.choice(desc_templates[cat]).format(
            city=city,
            n=random.choice([4, 5]),
            rooms=random.randint(20, 80),
            view=random.choice(views),
            year=random.choice(years_historic),
        )
        desc_fr = desc_fr_templates[cat].format(city=city)

        # Tags
        tags = random.sample(tag_pool, random.randint(3, 6))

        # Rooms (1-3 room types per hotel)
        rooms = []
        for rt_name, bed, sleeps in random.sample(room_types, random.randint(1, 3)):
            base_rate = round(random.uniform(59.99, 599.99), 2)
            room_tags = random.sample(room_tag_pool, random.randint(2, 4))
            room_view = random.choice(views).title()
            room_fr_view = random.choice(
                ["sur la ville", "sur le jardin", "sur la mer", "panoramique"]
            )
            rooms.append({
                "Description": f"{rt_name}, {bed} ({room_view} View)",
                "Description_fr": f"{rt_name}, {bed} (Vue {room_fr_view})",
                "Type": rt_name,
                "BaseRate": base_rate,
                "BedOptions": bed,
                "SleepsCount": sleeps,
                "SmokingAllowed": random.random() < 0.1,
                "Tags": room_tags,
            })

        rating = round(random.uniform(2.5, 5.0), 1)
        reno_year = random.choice(renovation_years)

        hotel = {
            "@search.action": "upload",
            "HotelId": str(i),
            "HotelName": name,
            "Description": desc,
            "Description_fr": desc_fr,
            "Category": cat,
            "Tags": tags,
            "ParkingIncluded": random.random() < 0.6,
            "LastRenovationDate": (
                f"{reno_year}-{random.randint(1,12):02d}-"
                f"{random.randint(1,28):02d}T00:00:00Z"
            ),
            "Rating": rating,
            "Location": {
                "type": "Point",
                "coordinates": [
                    round(lon + random.uniform(-0.05, 0.05), 6),
                    round(lat + random.uniform(-0.05, 0.05), 6),
                ],
            },
            "Address": {
                "StreetAddress": f"{random.randint(1, 9999)} {random.choice(streets)}",
                "City": city,
                "StateProvince": state,
                "PostalCode": zipcode,
                "Country": country,
            },
            "Rooms": rooms,
        }
        hotels.append(hotel)

    return hotels


if __name__ == "__main__":
    hotels = generate_hotels()
    with open("sample_data/hotels_100.json", "w", encoding="utf-8") as f:
        json.dump(hotels, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(hotels)} hotels")
    cats = set(h["Category"] for h in hotels)
    cities = set(h["Address"]["City"] for h in hotels)
    print(f"Categories: {cats}")
    print(f"Cities: {len(cities)} unique")
    print(f"Sample: {hotels[0]['HotelName']} — {hotels[0]['Description'][:80]}...")
