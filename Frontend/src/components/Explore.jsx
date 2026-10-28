import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-routing-machine';
import 'leaflet-routing-machine/dist/leaflet-routing-machine.css';
import { basemapLayer, tiledMapLayer } from 'esri-leaflet';
import Chat from './Chat';
import './Explore.css';

// Vite never runs into the broken default marker PNG paths here — import
// the assets directly and re-register them.
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
	iconUrl: markerIcon,
	iconRetinaUrl: markerIcon2x,
	shadowUrl: markerShadow,
});

const searchNominatim = async (text) => {
	try {
		const r = await fetch(
			`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=${encodeURIComponent(text)}`,
		);
		const j = await r.json();
		return Array.isArray(j) ? j : [];
	} catch {
		return [];
	}
};

function Explore() {
	const mapEl = useRef(null);
	const mapRef = useRef(null);
	const routingRef = useRef(null);
	const markerRef = useRef(null);

	const [mode, setMode] = useState('search'); // tab: search | route
	const [query, setQuery] = useState('');
	const [results, setResults] = useState([]);
	const [resultsFor, setResultsFor] = useState(''); // text the list belongs to
	const [from, setFrom] = useState(null); // route slots: {label, lat, lon}
	const [to, setTo] = useState(null);
	const [fromText, setFromText] = useState('');
	const [toText, setToText] = useState('');
	const [slot, setSlot] = useState('from'); // which route input a search targets
	const [suggest, setSuggest] = useState(true); // dropdown opens on typing only

	// Ref mirror so Leaflet's closures always see the latest state.
	const stateRef = useRef({});
	useEffect(() => {
		stateRef.current = { mode, from, to, slot };
	});

	const [opacity, setOpacity] = useState(0.45);
	const [dest, setDest] = useState('');
	const [chatOpen, setChatOpen] = useState(true);

	// Map + layers + routing control, built once. StrictMode's dev
	// double-invoke would create map #1 and orphan its async callbacks
	// onto the removed map — defer past the synchronous cleanup instead.
	useEffect(() => {
		let map;
		let killed = false;
		const t = setTimeout(() => {
			if (killed) return;
			map = L.map(mapEl.current, {
				center: [21, 78],
				zoom: 5,
				zoomControl: false,
			});
			L.control.zoom({ position: 'bottomright' }).addTo(map);
			basemapLayer('Imagery').addTo(map);
			// transparent labels/boundaries overlay, blended over the satellite base
			map.labels = tiledMapLayer({
				url: 'https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer',
				opacity: 0.45,
			}).addTo(map);
			mapRef.current = map;

			const routing = L.Routing.control({
				position: 'topright',
				collapsible: true,
				addWaypoints: false,
				fitSelectedRoutes: true,
				show: false, // collapsed to a button until a route exists
				lineOptions: {
					styles: [{ color: '#1560bd', opacity: 0.9, weight: 5 }],
				},
			}).addTo(map);
			routing.getContainer().classList.add('lrm-empty');
			routing.on('routesfound', () => {
				routing.getContainer().classList.remove('lrm-empty');
				routing.show();
			});
			routingRef.current = routing;

			// In directions mode, taps fill From first, then To (then re-fill To).
			map.on('click', (e) => {
				const s = stateRef.current;
				if (s.mode !== 'route') return;
				const item = {
					label: 'Map point',
					lat: e.latlng.lat,
					lon: e.latlng.lng,
				};
				setSuggest(false);
				if (!s.from) {
					setFrom(item);
					setFromText(item.label);
					setSlot('from');
				} else {
					setTo(item);
					setToText(item.label);
					setSlot('to');
				}
			});
		}, 0);

		return () => {
			killed = true;
			clearTimeout(t);
			map?.remove();
		};
	}, []);

	// Route points feed the routing machine whenever either slot changes.
	useEffect(() => {
		if (!routingRef.current) return;
		const pts = [from, to]
			.filter(Boolean)
			.map((i) => L.Routing.waypoint([i.lat, i.lon]));
		routingRef.current.setWaypoints(pts);
	}, [from, to]);

	// Debounced suggestions for whichever input is active.
	const q = mode === 'route' ? (slot === 'to' ? toText : fromText) : query;
	useEffect(() => {
		if (q.trim().length < 3) return undefined;
		const t = setTimeout(async () => {
			const items = await searchNominatim(q);
			setResults(items);
			setResultsFor(q);
		}, 350);
		return () => clearTimeout(t);
	}, [q]);

	const short = (name) => name.split(',')[0];

	const pick = (r, target) => {
		const item = {
			label: short(r.display_name),
			lat: Number(r.lat),
			lon: Number(r.lon),
		};
		setSuggest(false);
		if (target === 'search') {
			markerRef.current?.remove();
			markerRef.current = L.marker([item.lat, item.lon]).addTo(
				mapRef.current,
			);
			mapRef.current.flyTo([item.lat, item.lon], 14);
			setQuery('');
		} else if (target === 'to') {
			setTo(item);
			setToText(item.label);
		} else {
			setFrom(item);
			setFromText(item.label);
		}
		setDest(item.label);
		setResults([]);
	};

	// submit: reuse ready suggestions, or fetch right now (Search / → / Enter)
	const commit = async (target) => {
		const t = target ?? slot;
		const text = t === 'search' ? query : t === 'to' ? toText : fromText;
		if (text.trim().length < 3) return;
		const fresh = text === resultsFor && results.length > 0;
		const res = fresh ? results : await searchNominatim(text);
		if (res[0]) pick(res[0], t);
	};

	const clearPlan = () => {
		setFrom(null);
		setTo(null);
		setFromText('');
		setToText('');
		setResults([]);
		routingRef.current?.hide();
		routingRef.current?.getContainer().classList.add('lrm-empty');
	};

	const toggleMode = (m) => {
		if (m === 'route') markerRef.current?.remove();
		setResults([]);
		// re-clicking the active Directions tab clears the plan
		if (m === mode && m === 'route') clearPlan();
		setMode(m);
	};

	const setBlend = (v) => {
		setOpacity(v);
		mapRef.current?.labels.setOpacity(v);
	};

	return (
		<section className="explore">
			<div className="map-wrap">
				<div ref={mapEl} className="map" />
				<div className="overlay-top">
					<div className="card">
						<div className="tabs" role="tablist">
							<button
								type="button"
								role="tab"
								aria-selected={mode === 'search'}
								className={mode === 'search' ? 'on' : ''}
								onClick={() => toggleMode('search')}>
								Search
							</button>
							<button
								type="button"
								role="tab"
								aria-selected={mode === 'route'}
								className={mode === 'route' ? 'on' : ''}
								onClick={() => toggleMode('route')}>
								Directions
							</button>
						</div>
						{mode === 'search' ? (
							<div className="row">
								<input
									className="field"
									type="text"
									value={query}
									onChange={(e) => {
										setQuery(e.target.value);
										setSuggest(true);
									}}
									onKeyDown={(e) => {
										if (e.key === 'Enter') {
											e.preventDefault();
											commit('search');
										}
									}}
									placeholder="Search places…"
									aria-label="Search places"
								/>
								<button
									className="go"
									type="button"
									onClick={() => commit('search')}
									disabled={query.trim().length < 3}>
									Search
								</button>
							</div>
						) : (
							<div className="rows">
								<div className="row">
									<span className="ab a" aria-hidden="true">
										A
									</span>
									<input
										className="field"
										type="text"
										value={fromText}
										onChange={(e) => {
											setFromText(e.target.value);
											setSlot('from');
											setSuggest(true);
										}}
										onFocus={() => setSlot('from')}
										onKeyDown={(e) => {
											if (e.key === 'Enter') {
												e.preventDefault();
												commit('from');
											}
										}}
										placeholder="Choose starting point… or tap the map"
										aria-label="Starting point"
									/>
									<button
										className="icon"
										type="button"
										onClick={() => commit('from')}
										disabled={fromText.trim().length < 3}
										aria-label="Set starting point">
										→
									</button>
								</div>
								<div className="row">
									<span className="ab b" aria-hidden="true">
										B
									</span>
									<input
										className="field"
										type="text"
										value={toText}
										onChange={(e) => {
											setToText(e.target.value);
											setSlot('to');
											setSuggest(true);
										}}
										onFocus={() => setSlot('to')}
										onKeyDown={(e) => {
											if (e.key === 'Enter') {
												e.preventDefault();
												commit('to');
											}
										}}
										placeholder="Choose destination… or tap the map"
										aria-label="Destination"
									/>
									<button
										className="icon"
										type="button"
										onClick={() => commit('to')}
										disabled={toText.trim().length < 3}
										aria-label="Set destination">
										→
									</button>
								</div>
								{/* one-tap reset (re-clicking the active tab also clears) */}
								{(from || to) && (
									<button
										className="clear"
										type="button"
										onClick={clearPlan}>
										Clear route
									</button>
								)}
							</div>
						)}
					</div>
					{suggest &&
						results.length > 0 &&
						resultsFor === q &&
						q.trim().length >= 3 && (
							<ul className="search-results">
								{results.map((r) => (
									<li
										key={r.place_id}
										onClick={() =>
											pick(
												r,
												mode === 'route'
													? slot
													: 'search',
											)
										}>
										{r.display_name}
									</li>
								))}
							</ul>
						)}
				</div>
				<label className="blend">
					Blend
					<input
						type="range"
						min="0"
						max="1"
						step="0.05"
						value={opacity}
						onChange={(e) => setBlend(Number(e.target.value))}
						aria-label="Overlay opacity"
					/>
				</label>
			</div>
			<Chat
				open={chatOpen}
				onToggle={() => setChatOpen(!chatOpen)}
				destination={dest}
			/>
		</section>
	);
}

export default Explore;
