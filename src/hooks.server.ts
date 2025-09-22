import type { ServerInit } from '@sveltejs/kit';

const POLL_INTERVAL: number = parseInt(<any>Bun.env.POLL_INTERVAL) || 60;

export const init: ServerInit = async () => {
	const afadWorker = () => {
		Bun.spawn({
			cmd: ['bun', '--bun', './src/lib/afad-worker.ts'],
			stdout: 'inherit',
			stderr: 'inherit'
		});
	};

	afadWorker();

	setInterval(afadWorker, POLL_INTERVAL * 1000);
};
