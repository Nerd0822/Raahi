import { useEffect, useState } from 'react';
import { authed, clearAuth } from './auth';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Cta from './components/Cta';
import Planner from './components/Planner';
import Footer from './components/Footer';
import Explore from './components/Explore';
import Trips from './components/Trips';
import Profile from './components/Profile';

function App() {
	const [user, setUser] = useState(null);
	const [page, setPage] = useState('explore'); // explore | trips | profile

	const restore = () => {
		authed('/api/auth/me/').then((u) => u && setUser(u));
	};

	useEffect(restore, []);

	const logout = () => {
		clearAuth();
		setUser(null);
		setPage('explore');
	};

	const navigate = (p) => {
		setPage(p);
		window.scrollTo({ top: 0 });
	};

	return (
		<div id="top">
			<Navbar user={user} page={page} onNavigate={navigate} />
			{user ? (
				page === 'profile' ? (
					<Profile
						user={user}
						onBack={() => navigate('explore')}
						onLogout={logout}
						onSaved={setUser}
					/>
				) : page === 'trips' ? (
					<Trips />
				) : (
					<Explore />
				)
			) : (
				<>
					<Hero />
					<Cta onAuthed={restore} />
					<Planner />
					<Footer />
				</>
			)}
		</div>
	);
}

export default App;
