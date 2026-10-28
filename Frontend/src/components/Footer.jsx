import { useEffect, useState } from 'react';
import './Footer.css';

function Footer() {
	const [apiMessage, setApiMessage] = useState(null);
	const [apiError, setApiError] = useState(false);

	useEffect(() => {
		fetch('/api/home/')
			.then((res) => (res.ok ? res.json() : Promise.reject(res)))
			.then((data) => setApiMessage(data.message))
			.catch(() => setApiError(true));
	}, []);

	return (
		<footer className="footer">
			<div className="base">
				<span className="logo">Raahi</span>
				<p>
					Plan less, wander more. · Photos: Wikimedia Commons ·{' '}
					{apiError
						? 'Backend unreachable'
						: apiMessage
							? `Backend says: "${apiMessage}"`
							: 'Pinging the backend…'}
				</p>
				<small>© 2026 Raahi</small>
			</div>
		</footer>
	);
}

export default Footer;
