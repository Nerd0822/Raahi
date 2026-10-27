import { useEffect, useState } from 'react';
import './Hero.css';

function Hero() {
	const [apiMessage, setApiMessage] = useState(null);
	const [apiError, setApiError] = useState(false);

	useEffect(() => {
		fetch('/api/home/')
			.then((res) => (res.ok ? res.json() : Promise.reject(res)))
			.then((data) => setApiMessage(data.message))
			.catch(() => setApiError(true));
	}, []);

	return (
		<section className="hero">
			<h1>Your travel buddy, always one step ahead</h1>
			<p>
				Routes, buses, hotels and food spots, plus an AI that chats with
				you while you explore.
			</p>
			<button className="hero-button">Get started</button>
			<p className={apiError ? 'hero-api hero-api-error' : 'hero-api'}>
				{apiError
					? '⚠️ Backend unreachable'
					: apiMessage
						? `Backend says: "${apiMessage}"`
						: 'Pinging the backend…'}
			</p>
		</section>
	);
}

export default Hero;
