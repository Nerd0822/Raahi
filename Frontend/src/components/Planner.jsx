import { useEffect, useRef, useState } from 'react';
import anime from 'animejs';
import './Planner.css';

const FEATURES = ['Smart routes', 'Live timings', 'Stays & food', 'AI guide'];

const PLACES = [
	{
		slug: 'taj-mahal',
		name: 'Taj Mahal, Agra',
		plan: [
			'Delhi → Agra: Gatimaan Express, AC bus or private cab, compared for your dates.',
			'Monument closed on Mondays; the sunrise slot sees the thinnest crowds.',
			'Riverside havelis and rooftop thali spots, filtered by your budget.',
			'"Two days is enough — add Agra Fort and sunset at Mehtab Bagh."',
		],
	},
	{
		slug: 'golden-temple',
		name: 'Golden Temple, Amritsar',
		plan: [
			'Delhi → Amritsar: Shatabdi, Volvo or overnight train, side by side.',
			'Langar runs all day; the evening Palki ceremony is the busiest hour.',
			'Guest-house rooms and Old City Punjabi food within walking distance.',
			'"Pair it with the Wagah border ceremony — taxi plan ready."',
		],
	},
	{
		slug: 'kerala',
		name: 'Kerala backwaters',
		plan: [
			'Kochi → Alleppey: ferry, cab or bus connections tuned to houseboat check-in.',
			'Houseboats board at noon — arrival buffers are built into the route.',
			'Backwater homestays and toddy-shop seafood stops by price.',
			'"One night on the water is plenty — save the rest for Munnar tea hills."',
		],
	},
	{
		slug: 'hawa-mahal',
		name: 'Hawa Mahal, Jaipur',
		plan: [
			'Delhi → Jaipur: fast train, bus or cab door to door.',
			'Morning bazaar hours beat the afternoon facade crowds.',
			'Heritage havelis in the old city, from budget stays up.',
			'"Two days cover Amber Fort, the stepwells and sunrise at the Mahal."',
		],
	},
	{
		slug: 'great-wall',
		name: 'Great Wall, China',
		plan: [
			'Beijing → Badaling or Mutianyu: train, tourist bus or private driver, in one view.',
			'Cable-car queue times and clear-weather windows are built into the plan.',
			'Village guesthouses near Mutianyu, quieter than the city hotels.',
			'"Mutianyu for photos; Juyongguan if your time is short."',
		],
	},
];

function Planner() {
	const [active, setActive] = useState(0);
	const [seen, setSeen] = useState(false);
	const ref = useRef(null);

	useEffect(() => {
		const io = new IntersectionObserver(
			([entry]) => {
				if (entry.isIntersecting) {
					setSeen(true);
					io.disconnect();
				}
			},
			{ threshold: 0.2 },
		);
		io.observe(ref.current);
		return () => io.disconnect();
	}, []);

	useEffect(() => {
		if (!seen || window.matchMedia('(prefers-reduced-motion: reduce)').matches)
			return;
		anime({
			targets: ref.current.querySelectorAll('[data-row]'),
			opacity: [0, 1],
			translateY: [10, 0],
			delay: anime.stagger(70),
			duration: 380,
			easing: 'easeOutQuad',
		});
		anime({
			targets: ref.current.querySelector('[data-media]'),
			opacity: [0.35, 1],
			duration: 420,
			easing: 'easeOutQuad',
		});
	}, [seen, active]);

	const place = PLACES[active];

	return (
		<section id="places" className="section" ref={ref}>
			<h2>What Raahi does — on a real trip</h2>
			<div className="rail" aria-label="Pick a destination">
				{PLACES.map((p, i) => (
					<button
						key={p.slug}
						type="button"
						className={`rail-btn${i === active ? ' is-active' : ''}`}
						aria-pressed={i === active}
						onClick={() => setActive(i)}
					>
						<img src={`/places/${p.slug}.jpg`} alt="" loading="lazy" />
						<span>{p.name}</span>
					</button>
				))}
			</div>
			<article className="plan" aria-live="polite">
				<div className="media" data-media>
					<img src={`/places/${place.slug}.jpg`} alt={place.name} />
				</div>
				<div className="rows">
					{place.plan.map((line, i) => (
						<div className="row" data-row key={i}>
							<span className="num" aria-hidden="true">
								{String(i + 1).padStart(2, '0')}
							</span>
							<div>
								<strong>{FEATURES[i]}</strong>
								<p>{line}</p>
							</div>
						</div>
					))}
				</div>
			</article>
		</section>
	);
}

export default Planner;
