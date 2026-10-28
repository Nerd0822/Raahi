import { useEffect, useRef, useState } from 'react';
import { authed } from '../auth';
import './Chat.css';

function Chat({ open, onToggle, destination }) {
	const [messages, setMessages] = useState([
		{ role: 'ai', text: 'Hi! Ask me about places, routes or food.' },
	]);
	const [draft, setDraft] = useState('');
	const [busy, setBusy] = useState(false);
	const listRef = useRef(null);

	useEffect(() => {
		listRef.current?.scrollTo(0, listRef.current.scrollHeight);
	}, [messages]);

	const send = async (e) => {
		e.preventDefault();
		const text = draft.trim();
		if (!text || busy) return;
		setMessages((m) => [...m, { role: 'user', text }]);
		setDraft('');
		setBusy(true);
		try {
			const data = await authed('/api/chat/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ destination, message: text }),
			});
			setMessages((m) => [
				...m,
				{ role: 'ai', text: data?.reply ?? 'The AI guide is unavailable right now.' },
			]);
		} catch {
			setMessages((m) => [...m, { role: 'ai', text: 'Network hiccup — try again.' }]);
		} finally {
			setBusy(false);
		}
	};

	return (
		<>
			<button
				type="button"
				className={`chat-fab${open ? ' hidden' : ''}`}
				onClick={onToggle}
				aria-label="Open chat"
			>
				Ask Raahi
			</button>
			<aside className={`chat${open ? '' : ' collapsed'}`}>
				<header>
					<strong>Ask Raahi</strong>
					<button type="button" onClick={onToggle} aria-label="Collapse chat">
						›
					</button>
				</header>
				{destination && <p className="ctx">Looking at {destination}</p>}
				<ul className="chat-list" ref={listRef}>
					{messages.map((m, i) => (
						// Repeating text is impossible (index-based never reordered).
						<li key={i} className={m.role}>
							{m.text}
						</li>
					))}
				</ul>
				<form onSubmit={send}>
					<input
						value={draft}
						onChange={(e) => setDraft(e.target.value)}
						placeholder={destination ? `Ask about ${destination}…` : 'Ask anything…'}
						aria-label="Chat message"
					/>
					<button className="button small" type="submit" disabled={busy || !draft.trim()}>
						Send
					</button>
				</form>
			</aside>
		</>
	);
}

export default Chat;
