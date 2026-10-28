import { useState } from 'react';
import { authed } from '../auth';
import './Profile.css';

function Profile({ user, onBack, onLogout, onSaved }) {
	const [firstName, setFirstName] = useState(user.first_name || '');
	const [bio, setBio] = useState(user.bio || '');
	const [birthDate, setBirthDate] = useState(user.birth_date || '');
	const [preview, setPreview] = useState(user.profile_picture || '');
	const [file, setFile] = useState(null);
	const [status, setStatus] = useState('');

	const initial = (user.username || '?').charAt(0).toUpperCase();
	const joined = user.date_joined
		? new Date(user.date_joined).toLocaleDateString(undefined, {
				month: 'long',
				year: 'numeric',
			})
		: null;

	const choose = (e) => {
		const f = e.target.files?.[0];
		if (!f) return;
		if (!f.type.startsWith('image/')) {
			setStatus('Please choose an image file.');
			return;
		}
		if (f.size > 2 * 1024 * 1024) {
			setStatus('Image must be under 2 MB.');
			return;
		}
		setFile(f);
		setPreview(URL.createObjectURL(f));
		setStatus('');
	};

	const save = async (e) => {
		e.preventDefault();
		setStatus('saving');
		const fd = new FormData();
		fd.append('first_name', firstName);
		fd.append('bio', bio);
		if (birthDate) fd.append('birth_date', birthDate);
		if (file) fd.append('profile_picture', file);
		const updated = await authed('/api/auth/me/', { method: 'PATCH', body: fd });
		if (updated) {
			onSaved(updated);
			setStatus('Saved');
		} else {
			setStatus('Could not save. Try again.');
		}
	};

	return (
		<main className="profile">
			<form className="profile-card" onSubmit={save}>
				<label className="avatar-pick">
					{preview ? (
						<img src={preview} alt="Profile" />
					) : (
						<span className="avatar">{initial}</span>
					)}
					<input type="file" accept="image/*" onChange={choose} hidden />
					<span className="pick-hint">Change photo</span>
				</label>
				<h1>{firstName || user.username}</h1>
				<p className="mail">{user.email}</p>

				<label className="f">
					<span>Full name</span>
					<input
						type="text"
						value={firstName}
						onChange={(e) => setFirstName(e.target.value)}
						maxLength={150}
						placeholder="Your name"
					/>
				</label>
				<label className="f">
					<span>Bio</span>
					<textarea
						value={bio}
						onChange={(e) => setBio(e.target.value)}
						maxLength={500}
						rows={3}
						placeholder="A line about your travels"
					/>
				</label>
				<label className="f">
					<span>Birth date</span>
					<input
						type="date"
						value={birthDate}
						onChange={(e) => setBirthDate(e.target.value)}
					/>
				</label>

				<div className="profile-actions">
					<button className="button" type="submit" disabled={status === 'saving'}>
						{status === 'saving' ? 'Saving…' : 'Save changes'}
					</button>
				</div>
				{status && status !== 'saving' && <p className="note">{status}</p>}

				<div className="profile-actions secondary">
					<button className="button ghost" type="button" onClick={onBack}>
						Back to map
					</button>
					<button className="button ghost" type="button" onClick={onLogout}>
						Log out
					</button>
				</div>
				{joined && <p className="joined">Member since {joined}</p>}
			</form>
		</main>
	);
}

export default Profile;
