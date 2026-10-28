import { useEffect, useState } from 'react';
import { authed, clearAuth } from './auth';
import Navbar from './components/Navbar';
import Landing from './components/Landing';
import Login from './components/Login';
import Explore from './components/Explore';
import Trips from './components/Trips';
import Profile from './components/Profile';

function App() {
	const [user, setUser] = useState(null);
	const [page, setPage] = useState('home'); // home | explore | trips | profile
	const [openTripId, setOpenTripId] = useState(null);
	const [authOpen, setAuthOpen] = useState(false);
	const [authAfter, setAuthAfter] = useState(null);

	const restore = async () => {
		const current = await authed('/api/auth/me/');
		if (current) setUser(current);
		return current || null;
	};

	useEffect(() => {
		let active = true;
		authed('/api/auth/me/').then((current) => {
			if (active && current) setUser(current);
		});
		return () => {
			active = false;
		};
	}, []);

	// Store the follow-up action so a prompt submitted before sign-in can
	// generate as soon as the tokens are saved.
	const requestAuth = (after) => {
		setAuthAfter(() => after || null);
		setAuthOpen(true);
	};

	const finishAuth = async () => {
		setAuthOpen(false);
		const next = authAfter;
		setAuthAfter(null);
		const current = await restore();
		if (next) next(current);
	};

	const navigate = (target) => {
		if (target !== 'home' && !user) {
			requestAuth(() => {
				setOpenTripId(null);
				setPage(target);
				window.scrollTo({ top: 0 });
			});
			return;
		}
		setOpenTripId(null);
		setPage(target);
		window.scrollTo({ top: 0 });
	};

	const openTrips = (id) => {
		setOpenTripId(id ?? null);
		setPage('trips');
		window.scrollTo({ top: 0 });
	};

	const logout = () => {
		clearAuth();
		setUser(null);
		setPage('home');
		setOpenTripId(null);
	};

	const closeAuth = () => {
		setAuthOpen(false);
		setAuthAfter(null);
	};

	const inApp = user && page !== 'home';

	return (
		<div id="top">
			<Navbar
				user={user}
				page={page}
				onNavigate={navigate}
				onSignIn={() => requestAuth()}
			/>

			{!inApp && (
				<Landing
					user={user}
					onNeedAuth={requestAuth}
					onOpenTrips={openTrips}
					onExplore={() => navigate('explore')}
					onSignIn={() => requestAuth()}
				/>
			)}

			{user && page === 'explore' && <Explore />}
			{user && page === 'trips' && <Trips initialPlanId={openTripId} />}
			{user && page === 'profile' && (
				<Profile
					user={user}
					onBack={() => navigate('home')}
					onLogout={logout}
					onSaved={setUser}
				/>
			)}

			{authOpen && <Login onClose={closeAuth} onAuthed={finishAuth} />}
		</div>
	);
}

export default App;
