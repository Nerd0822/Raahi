import './Hero.css';

const EXAMPLES = [
	'3 relaxed days in Jaipur from Delhi',
	'A week in Kerala in December',
	'Weekend in Amritsar with my parents',
];

function Hero({
	prompt,
	start,
	onPrompt,
	onStart,
	onSubmit,
	busy,
	error,
	user,
}) {
	return (
		<section className="hero" id="plan">
			<div className="hero-inner">
				<p className="hero-eyebrow">AI itinerary planner</p>
				<h1>Your next trip, planned around you.</h1>
				<p className="hero-sub">
					Tell Raahi where you are going and how you like to travel. Get a
					day-by-day plan with stops, timings and rough costs — then make it
					yours.
				</p>

				<form
					className="plan-box"
					onSubmit={(e) => {
						e.preventDefault();
						onSubmit();
					}}
				>
					<label className="sr-only" htmlFor="trip-prompt">
						Describe your trip
					</label>
					<textarea
						id="trip-prompt"
						rows={3}
						value={prompt}
						onChange={(e) => onPrompt(e.target.value)}
						maxLength={1000}
						placeholder="Three relaxed days in Jaipur from Delhi in November — heritage walks, street food, a good rooftop dinner, mid-range budget."
					/>
					<div className="plan-controls">
						<label className="plan-date">
							<span>
								Start date <em>optional</em>
							</span>
							<input
								type="date"
								value={start}
								onChange={(e) => onStart(e.target.value)}
							/>
						</label>
						<button
							className="button plan-submit"
							type="submit"
							disabled={busy}
						>
							{busy ? 'Planning your trip…' : 'Plan my trip'}
						</button>
					</div>
					<div className="plan-hint-row">
						<p>
							{user
								? 'New plans are saved to Trips automatically.'
								: 'You will sign in once, then the plan saves to your trips.'}
						</p>
						<span>No dates? Raahi keeps the days flexible.</span>
					</div>
					{busy && (
						<p className="plan-status" role="status">
							<span aria-hidden="true" />
							Raahi is mapping the days. This can take up to a minute.
						</p>
					)}
					{error && (
						<p className="plan-error" role="alert">
							{error}
						</p>
					)}
				</form>

				<div className="hero-examples" aria-label="Example trips">
					<span>Try:</span>
					{EXAMPLES.map((example) => (
						<button
							key={example}
							type="button"
							onClick={() => onPrompt(example)}
						>
							{example}
						</button>
					))}
				</div>
			</div>
		</section>
	);
}

export default Hero;
