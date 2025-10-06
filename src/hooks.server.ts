import type { ServerInit } from '@sveltejs/kit';

const POLL_INTERVAL: number = parseInt(<any>Bun.env.POLL_INTERVAL) || 60;

export const init: ServerInit = async () => {
	const EqWorker = () => {
		Bun.spawn({
			cmd: ['bun', '--bun', './src/lib/eq-worker.ts'],
			stdout: 'inherit',
			stderr: 'inherit'
		});
	};

	EqWorker();

	setInterval(EqWorker, POLL_INTERVAL * 1000);
};
