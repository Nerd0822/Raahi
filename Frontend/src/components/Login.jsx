import { useState } from 'react';
import { saveAuth } from '../auth';
import './Login.css';

const ENDPOINT = { login: '/api/auth/login/', signup: '/api/auth/register/' };

function Login({ onClose, onAuthed }) {
	const [mode, setMode] = useState('login');
	const [error, setError] = useState(null);
	const [busy, setBusy] = useState(false);

	const submit = async (e) => {
		e.preventDefault();
		setBusy(true);
		setError(null);
		const data = Object.fromEntries(new FormData(e.currentTarget));
		// SimpleJWT authenticates on username; we mirror email into it.
		const payload =
			mode === 'login' ? { username: data.email, password: data.password } : data;
		try {
			const res = await fetch(ENDPOINT[mode], {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload),
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok) {
				const first = Object.values(body)[0];
				setError(
					res.status === 401
						? 'Wrong email or password.'
						: Array.isArray(first)
							? first[0]
							: typeof first === 'string'
								? first
								: 'Something went wrong.',
				);
				return;
			}
			saveAuth(body); // {access, refresh} — logged in the instant it returns
			onAuthed();
			onClose();
		} catch {
			setError('Network error — is the backend running?');
		} finally {
			setBusy(false);
		}
	};

	return (
		<div
			className="login-overlay"
			role="dialog"
			aria-modal="true"
			aria-labelledby="login-title"
			onClick={onClose}
			onKeyDown={(e) => {
				if (e.key === 'Escape') onClose();
			}}
		>
			<form
				className="login-card"
				onClick={(e) => e.stopPropagation()}
				onSubmit={submit}
			>
				<span className="login-logo" aria-hidden="true">
					Raahi
				</span>
				<h2 id="login-title">
					{mode === 'login' ? 'Welcome back' : 'Create your account'}
				</h2>
				<label>
					Email or username
					<input
						type="text"
						name="email"
						required
						placeholder="you@example.com"
						autoFocus
					/>
				</label>
				<label>
					Password
					<input
						type="password"
						name="password"
						required
						placeholder="••••••••"
					/>
				</label>
				{error && (
					<p className="login-error" role="alert">
						{error}
					</p>
				)}
				<button className="button" type="submit" disabled={busy}>
					{mode === 'login' ? 'Log in' : 'Sign up'}
				</button>
				<p className="login-switch">
					{mode === 'login' ? 'New to Raahi?' : 'Already have an account?'}{' '}
					<button
						type="button"
						onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
					>
						{mode === 'login' ? 'Create one' : 'Log in'}
					</button>
				</p>
				<button
					type="button"
					className="login-close"
					aria-label="Close"
					onClick={onClose}
				>
					×
				</button>
			</form>
		</div>
	);
}

export default Login;
