import './Navbar.css';

function Navbar({ user, page, onNavigate, onSignIn }) {
	const initial = (user?.username || '?').charAt(0).toUpperCase();
	const active = (name) => (page === name ? 'active' : '');

	return (
		<nav className="navbar">
			<button type="button" className="logo" onClick={() => onNavigate('home')}>
				Raahi
			</button>
			<div className="nav-right">
				<div className="nav-links">
					<button
						type="button"
						className={active('home')}
						onClick={() => onNavigate('home')}
					>
						Plan a trip
					</button>
					<button
						type="button"
						className={active('explore')}
						onClick={() => onNavigate('explore')}
					>
						Explore
					</button>
					{user ? (
						<button
							type="button"
							className={active('trips')}
							onClick={() => onNavigate('trips')}
						>
							Trips
						</button>
					) : (
						<button type="button" className="nav-cta" onClick={onSignIn}>
							Sign in
						</button>
					)}
				</div>
				{user && (
					<button
						type="button"
						className={`avatar${page === 'profile' ? ' active' : ''}`}
						onClick={() => onNavigate('profile')}
						aria-label="Open profile"
					>
						{user.profile_picture ? (
							<img src={user.profile_picture} alt="" />
						) : (
							initial
						)}
					</button>
				)}
			</div>
		</nav>
	);
}

export default Navbar;
