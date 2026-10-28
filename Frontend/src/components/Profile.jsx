import { useEffect, useRef, useState } from 'react';
import { authed } from '../auth';
import './Profile.css';

function Profile({ user, onBack, onLogout, onSaved }) {
	const [firstName, setFirstName] = useState(user.first_name || '');
	const [bio, setBio] = useState(user.bio || '');
	const [birthDate, setBirthDate] = useState(user.birth_date || '');
	const [preview, setPreview] = useState(user.profile_picture || '');
	const [file, setFile] = useState(null);
	const [status, setStatus] = useState('');
	const inputRef = useRef(null);
	const previewUrl = useRef('');

	const initial = (user.username || '?').charAt(0).toUpperCase();
	const joined = user.date_joined
		? new Date(user.date_joined).toLocaleDateString(undefined, {
				month: 'long',
				year: 'numeric',
			})
		: null;

	const dropPreview = () => {
		if (previewUrl.current) {
			URL.revokeObjectURL(previewUrl.current);
			previewUrl.current = '';
		}
	};

	useEffect(() => dropPreview, []);

	const resetSelection = (message) => {
		dropPreview();
		setFile(null);
		setPreview(user.profile_picture || '');
		if (inputRef.current) inputRef.current.value = '';
		setStatus(message);
	};

	const choose = (e) => {
		const f = e.target.files?.[0];
		if (!f) return;
		if (!f.type.startsWith('image/')) {
			resetSelection('Please choose an image file.');
			return;
		}
		if (f.size > 2 * 1024 * 1024) {
			resetSelection('Image must be under 2 MB.');
			return;
		}
		dropPreview();
		previewUrl.current = URL.createObjectURL(f);
		setFile(f);
		setPreview(previewUrl.current);
		setStatus('');
	};

	const saved = (updated) => {
		dropPreview();
		setFile(null);
		setPreview(updated.profile_picture || '');
		if (inputRef.current) inputRef.current.value = '';
		onSaved(updated);
		setStatus('Saved');
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
			saved(updated);
		} else {
			setStatus('Could not save. Try again.');
		}
	};

	const removePhoto = async () => {
		setStatus('saving');
		const fd = new FormData();
		fd.append('remove_profile_picture', 'true');
		const updated = await authed('/api/auth/me/', { method: 'PATCH', body: fd });
		if (updated) {
			saved(updated);
		} else {
			setStatus('Could not remove the photo. Try again.');
		}
	};

	return (
		<main className="profile">
			<form className="profile-card" onSubmit={save}>
				<div className="avatar-block">
					<label className="avatar-pick">
						{preview ? (
							<img src={preview} alt="Profile" />
						) : (
							<span className="avatar">{initial}</span>
						)}
						<input
							ref={inputRef}
							type="file"
							accept="image/*"
							onChange={choose}
							hidden
						/>
						<span className="pick-hint">Change photo</span>
					</label>
					{preview && (
						<button
							type="button"
							className="avatar-remove"
							onClick={removePhoto}
							disabled={status === 'saving'}
						>
							Remove photo
						</button>
					)}
				</div>
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
				{status && status !== 'saving' && (
					<p className="note" role="status">
						{status}
					</p>
				)}

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
