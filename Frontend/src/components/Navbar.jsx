import './Navbar.css';

function Navbar({ user, page, onNavigate }) {
	const initial = (user?.username || '?').charAt(0).toUpperCase();

	return (
		<nav className="navbar">
			<button type="button" className="logo" onClick={() => onNavigate('explore')}>
				Raahi
			</button>
			{user && (
				<div className="nav-right">
					<div className="nav-links">
						<button
							type="button"
							className={page === 'explore' ? 'active' : ''}
							onClick={() => onNavigate('explore')}
						>
							Explore
						</button>
						<button
							type="button"
							className={page === 'trips' ? 'active' : ''}
							onClick={() => onNavigate('trips')}
						>
							Trips
						</button>
						<button
							type="button"
							className={page === 'profile' ? 'active' : ''}
							onClick={() => onNavigate('profile')}
						>
							Profile
						</button>
					</div>
					<button
						type="button"
						className="avatar"
						onClick={() => onNavigate('profile')}
						aria-label="Open profile"
					>
						{user.profile_picture ? (
							<img src={user.profile_picture} alt="" />
						) : (
							initial
						)}
					</button>
				</div>
			)}
		</nav>
	);
}

export default Navbar;
