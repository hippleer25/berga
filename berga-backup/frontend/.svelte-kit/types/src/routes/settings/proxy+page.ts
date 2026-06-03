// @ts-nocheck
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load = () => {
	redirect(302, '/settings/appearance');
};
;null as any as PageLoad;