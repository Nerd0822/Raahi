import { useState } from 'react';
import Login from './Login';
import './Cta.css';

function Cta({ onAuthed }) {
	const [auth, setAuth] = useState(false);

	return (
		<>
			<section className="cta">
				<h2>Your next wonder is a chat away</h2>
				<p>Pick a destination, and one plan stands between you and the road.</p>
				<button type="button" className="button" onClick={() => setAuth(true)}>
					Get started
				</button>
			</section>
			{auth && <Login onClose={() => setAuth(false)} onAuthed={onAuthed} />}
		</>
	);
}

export default Cta;
