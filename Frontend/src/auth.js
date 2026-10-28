// ponytail: tokens in localStorage = XSS ceiling; httpOnly-cookie upgrade is
// the production step, do it when a real auth surface exists.
const KEY = 'raahi.auth';

const read = () => {
	try {
		return JSON.parse(localStorage.getItem(KEY));
	} catch {
		return null;
	}
};

export const saveAuth = (tokens) => localStorage.setItem(KEY, JSON.stringify(tokens));
export const clearAuth = () => localStorage.removeItem(KEY);

// authed(path, options?) -> parsed json, or null when not (or no longer)
// logged in. `options` may carry method/headers/body (POST chat, etc.).
// Transparently refreshes an expired access token exactly once.
export async function authed(path, options = {}) {
	const send = () =>
		fetch(path, {
			...options,
			headers: { ...options.headers, Authorization: `Bearer ${read().access}` },
		});

	let res = read()?.access
		? await send()
		: new Response(null, { status: 401 });

	if (res.status === 401 && read()?.refresh) {
		const r = await fetch('/api/auth/refresh/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ refresh: read().refresh }),
		});
		if (r.ok) {
			saveAuth({ access: (await r.json()).access, refresh: read().refresh });
			res = await send();
		} else {
			clearAuth();
		}
	}
	// 204 No Content (DELETE) has no body; callers still get a truthy success.
	if (!res.ok) return null;
	if (res.status === 204) return {};
	return res.json();
}