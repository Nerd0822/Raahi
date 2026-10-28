import { useEffect, useState } from 'react';
import { authed } from '../auth';
import './Trips.css';

const STATUS = { wishlist: 'Wishlist', planned: 'Planned', done: 'Done' };
const CATEGORIES = [
	['place', 'Place'],
	['food', 'Food'],
	['restaurant', 'Restaurant'],
	['transport', 'Transport'],
	['flight', 'Flight'],
	['stay', 'Stay'],
	['other', 'Other'],
];
const CATEGORY = Object.fromEntries(CATEGORIES);
const JSON_HEADERS = { 'Content-Type': 'application/json' };

const emptyDraft = { title: '', destination: '', start_date: '', end_date: '' };
const emptyItem = { category: 'place', name: '', time: '', cost: '', notes: '' };

const planForm = (p) => ({
	title: p.title || '',
	destination: p.destination || '',
	start_date: p.start_date || '',
	end_date: p.end_date || '',
	status: p.status || 'wishlist',
	notes: p.notes || '',
});

const shortDate = (d) =>
	d
		? new Date(`${d}T00:00:00`).toLocaleDateString(undefined, {
				day: 'numeric',
				month: 'short',
				year: 'numeric',
			})
		: '';

const dateRange = (start, end) => {
	if (start && end) return `${shortDate(start)} – ${shortDate(end)}`;
	return shortDate(start || end) || 'Dates not set';
};

const when = (iso) =>
	iso
		? new Date(iso).toLocaleString(undefined, {
				day: 'numeric',
				month: 'short',
				hour: 'numeric',
				minute: '2-digit',
			})
		: '';

const money = (cost) => (cost ? `₹${Number(cost).toLocaleString('en-IN')}` : '');

function Trips() {
	const [plans, setPlans] = useState(null);
	const [error, setError] = useState('');
	const [creating, setCreating] = useState(false);
	const [draft, setDraft] = useState(emptyDraft);
	const [selected, setSelected] = useState(null);
	const [form, setForm] = useState(null);
	const [item, setItem] = useState(emptyItem);
	const [busy, setBusy] = useState('');
	const [flash, setFlash] = useState('');

	useEffect(() => {
		let alive = true;
		authed('/api/plans/').then((data) => {
			if (!alive) return;
			if (Array.isArray(data)) {
				setPlans(data);
			} else {
				setPlans([]);
				setError("Couldn't load your trips.");
			}
		});
		return () => {
			alive = false;
		};
	}, []);

	// clear success messages after a beat; keep errors visible
	useEffect(() => {
		if (flash !== 'Saved' && flash !== 'Stop added') return undefined;
		const t = setTimeout(() => setFlash(''), 2500);
		return () => clearTimeout(t);
	}, [flash]);

	const openPlan = (p) => {
		setSelected(p);
		setForm(planForm(p));
		setItem(emptyItem);
		setFlash('');
		setError('');
		setCreating(false);
	};

	const cancelCreate = () => {
		setCreating(false);
		setDraft(emptyDraft);
		setError('');
	};

	const create = async (e) => {
		e.preventDefault();
		if (!draft.title.trim() || !draft.destination.trim()) {
			setError('Add a title and a destination.');
			return;
		}
		setBusy('create');
		setError('');
		const created = await authed('/api/plans/', {
			method: 'POST',
			headers: JSON_HEADERS,
			body: JSON.stringify({
				title: draft.title.trim(),
				destination: draft.destination.trim(),
				start_date: draft.start_date || null,
				end_date: draft.end_date || null,
			}),
		});
		setBusy('');
		if (!created) {
			setError("Couldn't create the trip. Check the dates.");
			return;
		}
		setPlans((prev) => [created, ...(prev || [])]);
		setDraft(emptyDraft);
		openPlan(created);
	};

	const save = async (e) => {
		e.preventDefault();
		if (!form.title.trim() || !form.destination.trim()) {
			setFlash('Title and destination are required.');
			return;
		}
		setBusy('plan');
		const updated = await authed(`/api/plans/${selected.id}/`, {
			method: 'PATCH',
			headers: JSON_HEADERS,
			body: JSON.stringify({
				...form,
				title: form.title.trim(),
				destination: form.destination.trim(),
				start_date: form.start_date || null,
				end_date: form.end_date || null,
			}),
		});
		setBusy('');
		if (!updated) {
			setFlash("Couldn't save. Check the dates and try again.");
			return;
		}
		setSelected(updated);
		setForm(planForm(updated));
		setPlans((prev) => (prev || []).map((p) => (p.id === updated.id ? updated : p)));
		setFlash('Saved');
	};

	const removePlan = async () => {
		if (!window.confirm('Delete this trip and all its stops?')) return;
		setBusy('delete-plan');
		const ok = await authed(`/api/plans/${selected.id}/`, { method: 'DELETE' });
		setBusy('');
		if (!ok) {
			setFlash("Couldn't delete the trip.");
			return;
		}
		setPlans((prev) => (prev || []).filter((p) => p.id !== selected.id));
		setSelected(null);
		setForm(null);
		setFlash('');
	};

	const addItem = async (e) => {
		e.preventDefault();
		if (!item.name.trim()) {
			setFlash('Give the stop a name.');
			return;
		}
		setBusy('item');
		const created = await authed('/api/plan-items/', {
			method: 'POST',
			headers: JSON_HEADERS,
			body: JSON.stringify({
				plan: selected.id,
				category: item.category,
				name: item.name.trim(),
				notes: item.notes.trim(),
				time: item.time ? new Date(item.time).toISOString() : null,
				cost: item.cost || null,
			}),
		});
		setBusy('');
		if (!created) {
			setFlash("Couldn't add the stop. Check the fields.");
			return;
		}
		setSelected((s) => ({ ...s, items: [...s.items, created] }));
		setPlans((prev) =>
			(prev || []).map((p) =>
				p.id === selected.id ? { ...p, items: [...p.items, created] } : p,
			),
		);
		setItem(emptyItem);
		setFlash('Stop added');
	};

	const removeItem = async (id) => {
		setBusy(`item-${id}`);
		const ok = await authed(`/api/plan-items/${id}/`, { method: 'DELETE' });
		setBusy('');
		if (!ok) {
			setFlash("Couldn't remove the stop.");
			return;
		}
		setSelected((s) => ({ ...s, items: s.items.filter((it) => it.id !== id) }));
		setPlans((prev) =>
			(prev || []).map((p) =>
				p.id === selected.id
					? { ...p, items: p.items.filter((it) => it.id !== id) }
					: p,
			),
		);
	};

	return (
		<main className="trips">
			{selected ? (
				<>
					<header className="trips-head">
						<div>
							<p className="kicker">My trips</p>
							<h1>{selected.title}</h1>
							<p className="trips-sub">
								{selected.destination} · {dateRange(selected.start_date, selected.end_date)}
							</p>
						</div>
						<button type="button" className="back-link" onClick={() => setSelected(null)}>
							← All trips
						</button>
					</header>

					{flash && (
						<p className="flash" role="status">
							{flash}
						</p>
					)}

					<div className="trip-columns">
						<form className="panel" onSubmit={save}>
							<div className="panel-head">
								<h2>Trip details</h2>
								<span className={`pill ${form.status}`}>{STATUS[form.status]}</span>
							</div>
							<div className="trip-fields">
								<label className="f wide">
									<span>Title</span>
									<input
										value={form.title}
										onChange={(e) => setForm({ ...form, title: e.target.value })}
										maxLength={200}
										required
									/>
								</label>
								<label className="f wide">
									<span>Destination</span>
									<input
										value={form.destination}
										onChange={(e) => setForm({ ...form, destination: e.target.value })}
										maxLength={200}
										required
									/>
								</label>
								<label className="f">
									<span>Start date</span>
									<input
										type="date"
										value={form.start_date}
										onChange={(e) => setForm({ ...form, start_date: e.target.value })}
									/>
								</label>
								<label className="f">
									<span>End date</span>
									<input
										type="date"
										value={form.end_date}
										onChange={(e) => setForm({ ...form, end_date: e.target.value })}
									/>
								</label>
								<label className="f">
									<span>Status</span>
									<select
										value={form.status}
										onChange={(e) => setForm({ ...form, status: e.target.value })}
									>
										{Object.entries(STATUS).map(([value, label]) => (
											<option key={value} value={value}>
												{label}
											</option>
										))}
									</select>
								</label>
								<label className="f wide">
									<span>Notes</span>
									<textarea
										rows={3}
										value={form.notes}
										onChange={(e) => setForm({ ...form, notes: e.target.value })}
										placeholder="Bookings, reminders, links…"
									/>
								</label>
							</div>
							<div className="trip-actions">
								<button className="button small" type="submit" disabled={busy === 'plan'}>
									{busy === 'plan' ? 'Saving…' : 'Save changes'}
								</button>
							</div>
						</form>

						<section className="panel">
							<div className="panel-head">
								<h2>Itinerary</h2>
								<span className="count">
									{selected.items.length} {selected.items.length === 1 ? 'stop' : 'stops'}
								</span>
							</div>

							{selected.items.length === 0 ? (
								<p className="trips-note">Nothing planned yet. Add the first stop below.</p>
							) : (
								<ul className="stops">
									{selected.items.map((it) => (
										<li className="stop" key={it.id}>
											<span className="cat">{CATEGORY[it.category] || it.category}</span>
											<div className="stop-main">
												<strong>{it.name}</strong>
												<span className="stop-meta">
													{[when(it.time), money(it.cost), it.notes]
														.filter(Boolean)
														.join(' · ')}
												</span>
											</div>
											<button
												type="button"
												className="remove"
												disabled={busy === `item-${it.id}`}
												onClick={() => removeItem(it.id)}
												aria-label={`Remove ${it.name}`}
											>
												Remove
											</button>
										</li>
									))}
								</ul>
							)}

							<form className="add-stop" onSubmit={addItem}>
								<h3>Add a stop</h3>
								<div className="trip-fields">
									<label className="f wide">
										<span>Name</span>
										<input
											value={item.name}
											onChange={(e) => setItem({ ...item, name: e.target.value })}
											placeholder="Hawa Mahal"
											maxLength={200}
											required
										/>
									</label>
									<label className="f">
										<span>Type</span>
										<select
											value={item.category}
											onChange={(e) => setItem({ ...item, category: e.target.value })}
										>
											{CATEGORIES.map(([value, label]) => (
												<option key={value} value={value}>
													{label}
												</option>
											))}
										</select>
									</label>
									<label className="f">
										<span>When</span>
										<input
											type="datetime-local"
											value={item.time}
											onChange={(e) => setItem({ ...item, time: e.target.value })}
										/>
									</label>
									<label className="f">
										<span>Cost (₹)</span>
										<input
											type="number"
											min="0"
											step="0.01"
											value={item.cost}
											onChange={(e) => setItem({ ...item, cost: e.target.value })}
											placeholder="0"
										/>
									</label>
									<label className="f wide">
										<span>Notes</span>
										<input
											value={item.notes}
											onChange={(e) => setItem({ ...item, notes: e.target.value })}
											placeholder="Timings, tickets, who's coming…"
										/>
									</label>
								</div>
								<div className="trip-actions">
									<button className="button small" type="submit" disabled={busy === 'item'}>
										{busy === 'item' ? 'Adding…' : 'Add stop'}
									</button>
								</div>
							</form>
						</section>
					</div>

					<div className="trip-footer">
						<button
							type="button"
							className="danger"
							onClick={removePlan}
							disabled={busy === 'delete-plan'}
						>
							{busy === 'delete-plan' ? 'Deleting…' : 'Delete trip'}
						</button>
					</div>
				</>
			) : (
				<>
					<header className="trips-head">
						<div>
							<p className="kicker">My trips</p>
							<h1>Where to next?</h1>
							<p className="trips-sub">Keep routes, stops and costs in one place.</p>
						</div>
						<button
							type="button"
							className="button"
							onClick={creating ? cancelCreate : () => setCreating(true)}
						>
							{creating ? 'Close' : 'New trip'}
						</button>
					</header>

					{error && (
						<p className="flash error" role="alert">
							{error}
						</p>
					)}

					{creating && (
						<form className="panel new-trip" onSubmit={create}>
							<div className="panel-head">
								<h2>New trip</h2>
							</div>
							<div className="trip-fields">
								<label className="f">
									<span>Title</span>
									<input
										value={draft.title}
										onChange={(e) => setDraft({ ...draft, title: e.target.value })}
										placeholder="Rajasthan road trip"
										maxLength={200}
										required
									/>
								</label>
								<label className="f">
									<span>Destination</span>
									<input
										value={draft.destination}
										onChange={(e) => setDraft({ ...draft, destination: e.target.value })}
										placeholder="Jaipur"
										maxLength={200}
										required
									/>
								</label>
								<label className="f">
									<span>Start date</span>
									<input
										type="date"
										value={draft.start_date}
										onChange={(e) => setDraft({ ...draft, start_date: e.target.value })}
									/>
								</label>
								<label className="f">
									<span>End date</span>
									<input
										type="date"
										value={draft.end_date}
										onChange={(e) => setDraft({ ...draft, end_date: e.target.value })}
									/>
								</label>
							</div>
							<div className="trip-actions">
								<button className="button small" type="submit" disabled={busy === 'create'}>
									{busy === 'create' ? 'Creating…' : 'Create trip'}
								</button>
								<button type="button" className="ghost" onClick={cancelCreate}>
									Cancel
								</button>
							</div>
						</form>
					)}

					{plans === null ? (
						<p className="trips-note">Loading trips…</p>
					) : plans.length === 0 ? (
						<div className="trips-empty">
							<h2>No trips yet</h2>
							<p>Name a trip, pick a destination, then build the itinerary stop by stop.</p>
							{!creating && (
								<button type="button" className="button" onClick={() => setCreating(true)}>
									Plan your first trip
								</button>
							)}
						</div>
					) : (
						<div className="trip-grid">
							{plans.map((p) => (
								<button
									type="button"
									className="trip-card"
									key={p.id}
									onClick={() => openPlan(p)}
								>
									<span className={`pill ${p.status}`}>{STATUS[p.status]}</span>
									<span className="trip-title">{p.title}</span>
									<span className="trip-dest">{p.destination}</span>
									<span className="trip-meta">
										{dateRange(p.start_date, p.end_date)} · {p.items.length}{' '}
										{p.items.length === 1 ? 'stop' : 'stops'}
									</span>
								</button>
							))}
						</div>
					)}
				</>
			)}
		</main>
	);
}

export default Trips;
