import { PLACES } from '../places';
import './Footer.css';

function Footer({ user, onExplore, onTrips, onSignIn }) {
	return (
		<footer className="footer">
			<div className="footer-inner">
				<div className="footer-brand">
					<span className="footer-logo">Raahi</span>
					<p>
						Plan less, wander more. Day-by-day itineraries for the way India
						travels.
					</p>
				</div>

				<div className="footer-col">
					<h2>Plan</h2>
					<a href="#plan">Plan a trip</a>
					<button type="button" onClick={onExplore}>
						Explore the map
					</button>
					{user ? (
						<button type="button" onClick={() => onTrips()}>
							My trips
						</button>
					) : (
						<button type="button" onClick={onSignIn}>
							Sign in
						</button>
					)}
				</div>

				<div className="footer-col">
					<h2>Destinations</h2>
					{PLACES.map((place) => (
						<a key={place.slug} href="#destinations">
							{place.city}
						</a>
					))}
				</div>

				<div className="footer-col">
					<h2>Raahi</h2>
					<a href="#how">How it works</a>
					<a href="#about">About</a>
					<a href="#faq">FAQ</a>
				</div>
			</div>

			<div className="footer-base">
				<small>© 2026 Raahi</small>
				<small>Photos: Wikimedia Commons</small>
			</div>
		</footer>
	);
}

export default Footer;
