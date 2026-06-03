<script lang="ts">
	import LogOut from '@lucide/svelte/icons/log-out';
	import { t } from 'svelte-i18n';
	import { ripple } from '$lib/actions/ripple';

	async function logout() {
		try {
			await fetch('/api/logout', { method: 'POST', credentials: 'include' });
		} finally {
			window.location.replace('/');
		}
	}
</script>

<div class="tab-panel">
	<h2 class="section-title">{$t('settings.account')}</h2>

	<div class="account-section">
		<button class="action-btn danger full-width" use:ripple onclick={logout}>
			<LogOut size={16} /><span>{$t('settings.logOut')}</span>
		</button>
	</div>
</div>

<style>
	.tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; }
	.section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }

	.account-section { display: flex; flex-direction: column; gap: 12px; }

	.action-btn {
		display: inline-flex; align-items: center; justify-content: center; gap: 6px;
		padding: 10px 16px; border-radius: 10px; border: 1px solid var(--color-base-300);
		background: transparent; color: var(--color-base-content); cursor: pointer;
		font-size: 13px; font-weight: 600; transition: all 130ms ease;
		position: relative; overflow: hidden;
	}
	.action-btn:hover { background: var(--color-base-200); }
	.action-btn:active { transform: scale(0.97); }
	.action-btn.full-width { width: 100%; }
	.action-btn.danger { border-color: color-mix(in oklch, var(--color-error) 50%, transparent); color: var(--color-error); }
	.action-btn.danger:hover { background: color-mix(in oklch, var(--color-error) 10%, transparent); }
</style>
