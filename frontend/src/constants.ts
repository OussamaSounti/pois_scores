export const CAT_ICONS: Record<string, string> = {
  Transport: '🚌',
  'Food & Drinks': '🍽',
  Healthcare: '🏥',
  Finance: '🏦',
  Education: '🎓',
  Shopping: '🛍',
  'Sport & Recreation': '⚽',
  'Tourism & Accommodation': '🏨',
  'Government & Public Service': '🏛',
  Religion: '🕌',
  Other: '📍',
  'Automotive & Traffic': '🚗',
};

/** Category colors for POI markers on map (prototype style) */
export const CAT_COLORS: Record<string, string> = {
  Transport: '#1a7fa8',
  'Food & Drinks': '#e07b39',
  Healthcare: '#d64545',
  Finance: '#c2622a',
  Education: '#6b58c2',
  Shopping: '#c2368a',
  'Sport & Recreation': '#1e9d65',
  'Tourism & Accommodation': '#3a7dd4',
  'Government & Public Service': '#607d94',
  Religion: '#8a6ac2',
  Other: '#8a93b2',
  'Automotive & Traffic': '#7a8ca0',
};

export const ACC_META: Record<string, { icon: string; label: string }> = {
  bus_stop: { icon: '🚌', label: 'Bus' },
  tram_stop: { icon: '🚋', label: 'Tram' },
  pharmacy: { icon: '💊', label: 'Pharmacy' },
  school: { icon: '🏫', label: 'School' },
  park: { icon: '🌳', label: 'Park' },
  mall: { icon: '🏬', label: 'Mall' },
  bank: { icon: '🏦', label: 'Bank' },
  hospital: { icon: '🏥', label: 'Hospital' },
  supermarket: { icon: '🛒', label: 'Supermkt' },
  restaurant: { icon: '🍽', label: 'Restaurant' },
  cafe: { icon: '☕', label: 'Café' },
  atm: { icon: '💳', label: 'ATM' },
  kindergarten: { icon: '🧒', label: 'Kinder' },
  clinic: { icon: '🩺', label: 'Clinic' },
  doctors: { icon: '👨‍⚕️', label: 'Doctor' },
  fast_food: { icon: '🍟', label: 'Fast Food' },
  fuel: { icon: '⛽', label: 'Fuel' },
  post_office: { icon: '📮', label: 'Post' },
  police: { icon: '🚔', label: 'Police' },
  railway_station: { icon: '🚂', label: 'Train' },
  taxi: { icon: '🚕', label: 'Taxi' },
};

/** Tooltip copy for score explanations */
export const SCORE_TOOLTIPS: Record<string, string> = {
  poi_count_1km: 'Number of points of interest (POIs) within a 1 km radius of the location.',
  poi_count_400m: 'Number of POIs within 400 m (roughly a 5‑minute walk).',
  n_categories:
    'Number of distinct super-categories (e.g. Transport, Healthcare) present within 1 km.',
  n_poi_types: 'Number of distinct POI types (fclass) within 1 km.',
  entropy:
    'Shannon entropy of the category distribution within 1 km. Higher = more balanced mix of categories.',
  entropy_fclass:
    'Shannon entropy of the POI-type (fclass) distribution within 1 km. Higher = more variety of types.',
  by_category: 'Count of POIs per super-category within 1 km.',
  accessibility_400m:
    'Whether key POI types (e.g. bus stop, pharmacy) are present within 400 m walk.',
  nearest_km: 'Distance in km from the location to the nearest POI in each category.',
  aggregate_score: 'Composite score 0–100 combining density, diversity, and accessibility.',
  dist_coast_km:
    'Geodesic distance (km) from this location to the nearest coastline. ' +
    'Closer values indicate beachfront or seafront properties.',
  land_buffer_fraction_1km:
    'Fraction of the 1 km analysis buffer that lies on land (0.5–1.0). ' +
    'Values below 1.0 mean part of the buffer extends into the sea; ' +
    'the aggregate score density component is corrected for this.',
};
