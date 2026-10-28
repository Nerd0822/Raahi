import { useState } from 'react';
import { authed } from '../auth';
import { PLACES } from '../places';
import Hero from './Hero';
import Footer from './Footer';
import './Landing.css';

const JSON_HEADERS = { 'Content-Type': 'application/json' };

const CATEGORY_LABEL = {
	place: 'Place',
	food: 'Food',
	restaurant: 'Restaurant',
	transport: 'Transport',
	flight: 'Flight',
	stay: 'Stay',
	other: 'Stop',
};

const FAQS = [
	{
		q: 'How does the AI planner work?',
		a: 'Describe the destination, dates and the kind of trip you want. Raahi turns that into a day-by-day itinerary with stops, timings and rough per-person costs. You can regenerate as often as you like.',
	},
	{
		q: 'Do I need an account?',
		a: 'You need to sign in to save a plan. You can write the prompt first — sign-in takes a moment and the plan is generated right after.',
	},
	{
		q: 'Can I edit the itinerary?',
		a: 'Yes. Every generated plan lands in Trips, where you can change the trip details, remove stops, add your own, and set a status and notes.',
	},
	{
		q: 'What if I do not know the dates yet?',
		a: 'Leave the start date blank. Raahi will structure the days without pinning them to a calendar, and you can add dates later in Trips.',
	},
	{
		q: 'How accurate are the costs?',
		a: 'Costs are rough estimates in rupees to help you compare options, not quotes. Confirm tickets, entry fees and room rates before you commit.',
	},
	{
		q: 'Does Raahi plan outside India?',
		a: 'Yes. Raahi is India-first — trains, buses, stays and street food are our comfort zone — but it also plans international trips.',
	},
];

const shortDate = (value) =>
	value
		? new Date(`${value}T12:00:00`).toLocaleDateString(undefined, {
				day: 'numeric',
				month: 'short',
			})
		: '';

const dateLabel = (plan) => {
	if (plan.start_date && plan.end_date) {
		return `${shortDate(plan.start_date)} – ${shortDate(plan.end_date)}`;
	}
	if (plan.start_date) return `From ${shortDate(plan.start_date)}`;
	return 'Flexible dates';
};

const scrollTo = (id) => {
	const target = document.getElementById(id);
	if (!target) return;
	const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	target.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
};

const groupDays = (items = []) => {
	const days = new Map();
	for (const item of items) {
		const number = Number(item.details?.day) || 1;
		if (!days.has(number)) days.set(number, []);
		days.get(number).push(item);
	}
	return [...days.entries()]
		.sort((a, b) => a[0] - b[0])
		.map(([number, stops]) => ({
			number,
			title: stops[0]?.details?.day_title || '',
			stops: [...stops].sort((a, b) =>
				(a.details?.time || '99:99').localeCompare(b.details?.time || '99:99'),
			),
		}));
};

function Itinerary({ plan, onOpenTrips, onReset }) {
	const days = groupDays(plan.items);
	return (
		<section className="itinerary" id="itinerary">
			<div className="itinerary-head">
				<div>
					<p className="kicker">Your AI itinerary</p>
					<h2>{plan.title}</h2>
					<p className="itinerary-meta">
						{plan.destination} · {dateLabel(plan)} · {days.length}{' '}
						{days.length === 1 ? 'day' : 'days'} · {plan.items.length} stops
					</p>
				</div>
				<span className="saved-pill">Saved to Trips</span>
			</div>

			{plan.notes && <p className="itinerary-summary">{plan.notes}</p>}

			<div className="day-list">
				{days.map((day) => (
					<article className="day-card" key={day.number}>
						<header className="day-head">
							<span className="day-number">Day {day.number}</span>
							<h3>{day.title || 'On the road'}</h3>
						</header>
						<ol className="day-stops">
							{day.stops.map((stop) => (
								<li className="day-stop" key={stop.id}>
									<span className="stop-time">
										{stop.details?.time || 'Anytime'}
									</span>
									<div className="stop-body">
										<span className="stop-cat">
											{CATEGORY_LABEL[stop.category] || 'Stop'}
										</span>
										<strong>{stop.name}</strong>
										{stop.notes && <p>{stop.notes}</p>}
									</div>
									{stop.cost !== null && stop.cost !== undefined && (
										<span className="stop-cost">
											{Number(stop.cost) > 0
												? `₹${Number(stop.cost).toLocaleString('en-IN')}`
												: 'Free'}
										</span>
									)}
								</li>
							))}
						</ol>
					</article>
				))}
			</div>

			<div className="itinerary-actions">
				<button
					type="button"
					className="button"
					onClick={() => onOpenTrips(plan.id)}
				>
					Open in Trips
				</button>
				<button type="button" className="ghost-button" onClick={onReset}>
					Plan another trip
				</button>
			</div>
		</section>
	);
}

function Landing({ user, onNeedAuth, onOpenTrips, onExplore, onSignIn }) {
	const [draft, setDraft] = useState({ prompt: '', start: '' });
	const [plan, setPlan] = useState(null);
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState('');

	const generate = async (request) => {
		setBusy(true);
		setError('');
		setPlan(null);
		try {
			const data = await authed('/api/plans/generate/', {
				method: 'POST',
				headers: JSON_HEADERS,
				body: JSON.stringify(request),
			});
			if (!data) {
				setError(
					"Raahi couldn't finish that plan. Try rephrasing the request or try again in a moment.",
				);
				return;
			}
			setPlan(data);
			setTimeout(() => scrollTo('itinerary'), 60);
		} catch {
			setError('Network error — is the backend running?');
		} finally {
			setBusy(false);
		}
	};

	const start = (prompt, startDate) => {
		const request = {
			prompt: prompt.trim(),
			start_date: startDate || null,
		};
		if (!request.prompt) {
			setError('Tell Raahi where you want to go.');
			return;
		}
		if (!user) {
			onNeedAuth(() => generate(request));
			return;
		}
		generate(request);
	};

	const submit = () => start(draft.prompt, draft.start);

	const planIdea = (idea) => {
		setDraft({ prompt: idea.prompt, start: '' });
		start(idea.prompt, '');
	};

	const pickDestination = (idea) => {
		setDraft({ prompt: idea.prompt, start: '' });
		setError('');
		scrollTo('plan');
	};

	const reset = () => {
		setPlan(null);
		setError('');
		setDraft({ prompt: '', start: '' });
		scrollTo('plan');
	};

	return (
		<main className="landing">
			<Hero
				prompt={draft.prompt}
				start={draft.start}
				onPrompt={(prompt) => setDraft((d) => ({ ...d, prompt }))}
				onStart={(start) => setDraft((d) => ({ ...d, start }))}
				onSubmit={submit}
				busy={busy}
				error={error}
				user={user}
			/>

			{busy && (
				<section className="plan-loading" aria-hidden="true">
					{[1, 2, 3].map((n) => (
						<div className="loading-card" key={n}>
							<span />
							<span />
							<span />
						</div>
					))}
				</section>
			)}

			{plan && (
				<Itinerary plan={plan} onOpenTrips={onOpenTrips} onReset={reset} />
			)}

			<section className="section ideas" id="itineraries">
				<div className="section-head">
					<p className="kicker">Curated starts</p>
					<h2>Latest itineraries</h2>
					<p>
						Routes from the Raahi map, ready for the AI to shape around your
						dates and pace.
					</p>
				</div>
				<div className="idea-grid">
					{PLACES.map((idea) => (
						<button
							type="button"
							className="idea-card"
							key={idea.slug}
							onClick={() => planIdea(idea)}
							disabled={busy}
						>
							<span className="idea-media">
								<img
									src={`/places/${idea.slug}.jpg`}
									alt=""
									loading="lazy"
								/>
								<span className="idea-days">{idea.days} days</span>
							</span>
							<span className="idea-body">
								<span className="idea-meta">
									{idea.city} · {idea.region}
								</span>
								<span className="idea-title">{idea.title}</span>
								<span className="idea-blurb">{idea.blurb}</span>
								<span className="idea-tags">
									{idea.tags.map((tag) => (
										<span key={tag}>{tag}</span>
									))}
								</span>
								<span className="idea-cta">
									Plan this trip <span aria-hidden="true">→</span>
								</span>
							</span>
						</button>
					))}
					<button
						type="button"
						className="idea-card idea-make"
						onClick={() => scrollTo('plan')}
					>
						<span className="idea-make-body">
							<span className="idea-meta">Somewhere else?</span>
							<span className="idea-title">Plan it from a sentence</span>
							<span className="idea-blurb">
								Name the place and the shape of the trip. Raahi writes the
								days, you change what you like.
							</span>
							<span className="idea-cta">
								Start planning <span aria-hidden="true">→</span>
							</span>
						</span>
					</button>
				</div>
			</section>

			<section className="steps-band" id="how">
				<div className="steps">
					<div className="section-head">
						<p className="kicker">How it works</p>
						<h2>From a sentence to a full plan</h2>
					</div>
					<div className="step-grid">
						<article>
							<span className="step-number">01</span>
							<h3>Describe the trip</h3>
							<p>
								Destination, dates, budget, pace, who is coming — a few
								details are enough to start.
							</p>
						</article>
						<article>
							<span className="step-number">02</span>
							<h3>AI shapes the days</h3>
							<p>
								Raahi drafts a day-by-day itinerary with stops, timings,
								costs and practical notes.
							</p>
						</article>
						<article>
							<span className="step-number">03</span>
							<h3>Make it yours</h3>
							<p>
								Open the plan in Trips, add or remove stops, then explore the
								route on the map.
							</p>
						</article>
					</div>
					<div className="steps-cta">
						<button
							type="button"
							className="button"
							onClick={() => scrollTo('plan')}
						>
							Start a plan
						</button>
					</div>
				</div>
			</section>

			<section className="about-band" id="about">
				<div className="about-card">
					<div>
						<p className="kicker">About Raahi</p>
						<h2>Built for the way India travels</h2>
						<p>
							Trains, buses, stays and street food — Raahi keeps the moving
							parts in one place. Plan with AI, check the map, then adjust the
							plan as the trip changes. No spreadsheets, no twelve open tabs.
						</p>
					</div>
					<div className="about-actions">
						<button type="button" className="button light" onClick={onExplore}>
							Explore the map
						</button>
						<button
							type="button"
							className="about-link"
							onClick={() => scrollTo('plan')}
						>
							Plan a trip
						</button>
					</div>
				</div>
			</section>

			<section className="section destinations" id="destinations">
				<div className="section-head">
					<p className="kicker">Start here</p>
					<h2>Popular destinations</h2>
					<p>Pick a place to load a starter prompt, then make it yours.</p>
				</div>
				<div className="dest-grid">
					{PLACES.map((idea) => (
						<button
							type="button"
							className="dest-card"
							key={idea.slug}
							onClick={() => pickDestination(idea)}
						>
							<strong>{idea.city}</strong>
							<span>{idea.region}</span>
							<em>{idea.days} day trip</em>
						</button>
					))}
				</div>
			</section>

			<section className="section faq" id="faq">
				<div className="section-head">
					<p className="kicker">Good to know</p>
					<h2>Questions, answered</h2>
				</div>
				<div className="faq-list">
					{FAQS.map((item) => (
						<details key={item.q}>
							<summary>{item.q}</summary>
							<p>{item.a}</p>
						</details>
					))}
				</div>
			</section>

			<Footer
				user={user}
				onExplore={onExplore}
				onTrips={onOpenTrips}
				onSignIn={onSignIn}
			/>
		</main>
	);
}

export default Landing;
