import { useEffect, useState } from 'react';
import anime from 'animejs';
import './Hero.css';

const WORDS = ['Routes', 'Buses', 'Stays', 'Food'];

function Hero() {
	const [word, setWord] = useState(0);

	useEffect(() => {
		const timer = setInterval(() => setWord((i) => (i + 1) % WORDS.length), 2200);
		return () => clearInterval(timer);
	}, []);

	useEffect(() => {
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		anime({
			targets: '[data-reveal]',
			opacity: [0, 1],
			translateY: [16, 0],
			delay: anime.stagger(110),
			duration: 520,
			easing: 'easeOutExpo',
		});
	}, []);

	return (
		<section className="hero">
			<h1 data-reveal>
				Your travel buddy, one step ahead on{' '}
				<span className="word" key={word}>
					{WORDS[word]}
				</span>
			</h1>
			<p data-reveal>
				Compare buses, trains, stays and food — with an AI guide that plans
				while you travel, across India and beyond.
			</p>
		</section>
	);
}

export default Hero;
