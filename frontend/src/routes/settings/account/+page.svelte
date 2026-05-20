<script lang="ts">
 import LogOut from '@lucide/svelte/icons/log-out';
 import Globe from '@lucide/svelte/icons/globe';
 import { t } from 'svelte-i18n';
 import { apiFetch } from '$lib/api';
 import { instance } from '$lib/stores/instance';
 import { auth } from '$lib/stores/auth';
 import { ripple } from '$lib/actions/ripple';

 let instanceUrl = $state(instance.getInstance());

 function saveInstance() {
   instance.setInstance(instanceUrl);
 }

 async function logout() {
   try {
     await apiFetch('/api/logout', { method: 'POST', credentials: 'include' });
   } finally {
      auth.setLoggedOut();
     window.location.replace('/');
   }
 }
</script>

<div class="tab-panel">
 <h2 class="section-title">{$t('settings.account')}</h2>

 <div class="account-section">
   <div class="instance-section">
     <label for="instance-setting" class="setting-label">{$t('settings.instanceLabel')}</label>
     <div class="instance-row">
       <div class="input-icon-wrap">
         <span class="input-icon"><Globe size={18} /></span>
         <input
           id="instance-setting"
           type="text"
           class="custom-input has-icon-left"
           placeholder={$t('settings.instancePlaceholder')}
           bind:value={instanceUrl}
           oninput={saveInstance}
         />
       </div>
     </div>
     <p class="setting-desc">{$t('settings.instanceDesc')}</p>
   </div>

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

.instance-section { display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; }
.setting-label { font-size: 13px; font-weight: 600; color: color-mix(in oklch, var(--color-base-content) 80%, transparent); padding-left: 2px; }
.setting-desc { font-size: 12px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: 0; line-height: 1.4; }
.input-icon-wrap { position: relative; display: flex; align-items: center; }
.custom-input { width: 100%; height: 44px; background: color-mix(in oklch, var(--color-base-200) 50%, transparent); border: 1px solid var(--color-base-300); border-radius: 10px; padding: 0 14px; font-size: 14px; color: var(--color-base-content); transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease; outline: none; }
.custom-input::placeholder { color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }
.custom-input:focus { background: var(--color-base-100); border-color: var(--color-accent); box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent); }
.custom-input.has-icon-left { padding-left: 42px; }
.input-icon { position: absolute; left: 14px; color: var(--color-accent); display: flex; align-items: center; pointer-events: none; z-index: 2; }
</style>
