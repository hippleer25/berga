<script lang="ts">
  import User from "@lucide/svelte/icons/user";
  import UserCircle from "@lucide/svelte/icons/user-circle";
  import Mail from "@lucide/svelte/icons/mail";
  import Lock from "@lucide/svelte/icons/lock";
  import Eye from "@lucide/svelte/icons/eye";
  import EyeClosed from "@lucide/svelte/icons/eye-closed";
  import ArrowLeft from '@lucide/svelte/icons/arrow-left';
  import Globe from '@lucide/svelte/icons/globe';

  import { t } from 'svelte-i18n';
  import { get } from 'svelte/store';
import { apiFetch, setNativeToken } from '$lib/api';
import { instance } from '$lib/stores/instance';
import { auth } from '$lib/stores/auth';

  let instanceUrl = $state(get(instance));
  let username = $state("");
  let password = $state("");
  let full_name = $state("");
  let email = $state("");
  let showPassword = $state(false);

  let message = $state("");
  let loading = $state(false);

	let usernameRef: HTMLInputElement;
	let fullNameRef: HTMLInputElement;
	let emailRef: HTMLInputElement;
	let passwordRef: HTMLInputElement;

	let instanceTimer: ReturnType<typeof setTimeout> | null = null;
	$effect(() => {
		if (instanceTimer) clearTimeout(instanceTimer);
		instanceTimer = setTimeout(() => {
			instance.setInstance(instanceUrl);
		}, 500);
	});

  function focusNext(nextRef: HTMLInputElement | undefined) {
    nextRef?.focus();
  }

  async function signup() {
    loading = true;
    message = "";

    try {
      const response = await apiFetch(`/api/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          username,
          password,
          full_name,
          email
        })
      });

      const data = await response.json();

      if (data.status === "success") {
        const isNative = !!(window as any).Capacitor?.isNativePlatform?.();
        if (isNative && data.access_token) {
          setNativeToken(data.access_token);
        }
        auth.setLoggedIn();
        window.location.href = '/home';
      } else {
        message = data.message || get(t)('signup.errorSignup');
      }

    } catch (err) {
      message = get(t)('signup.errorSignup');
    }

    loading = false;
  }
</script>

<div class="page-root page-root--centered">
    <div class="main-content login-layout">
        <div class="login-container">

            <!-- Header -->
            <div class="login-header">
                <h1 class="page-title">{$t('signup.title')}</h1>
                <p class="section-desc">{$t('signup.subtitle')}</p>
            </div>

  <!-- Form -->
  <div class="form-wrap">

  <!-- Instance URL -->
  <div class="form-group">
    <label for="instance" class="setting-label">{$t('signup.instanceLabel')}</label>
    <div class="input-icon-wrap">
      <span class="input-icon">
        <Globe size={18} />
      </span>
      <input
        id="instance"
        type="text"
        class="custom-input has-icon-left"
        placeholder={$t('signup.instancePlaceholder')}
        bind:value={instanceUrl}
        onkeydown={(e) => e.key === 'Enter' && focusNext(usernameRef)}
      />
    </div>
  </div>

  <!-- Username -->
                <div class="form-group">
                    <label for="username" class="setting-label">{$t('signup.accountLabel')}</label>
                    <div class="input-icon-wrap">
                        <span class="input-icon">
                            <User size={18} />
                        </span>
                        <input
                            id="username"
                            type="text"
                            class="custom-input has-icon-left"
                            placeholder="{$t('signup.accountPlaceholder')}"
                            bind:value={username}
                            bind:this={usernameRef}
                            onkeydown={(e) => e.key === 'Enter' && focusNext(fullNameRef)}
                        />
                    </div>
                </div>

                <!-- Full Name -->
                <div class="form-group">
                    <label for="full_name" class="setting-label">{$t('signup.fullNameLabel')}</label>
                    <div class="input-icon-wrap">
                        <span class="input-icon">
                            <UserCircle size={18} />
                        </span>
                        <input
                            id="full_name"
                            type="text"
                            class="custom-input has-icon-left"
                            placeholder="{$t('signup.fullNamePlaceholder')}"
                            bind:value={full_name}
                            bind:this={fullNameRef}
                            onkeydown={(e) => e.key === 'Enter' && focusNext(emailRef)}
                        />
                    </div>
                </div>

                <!-- Email -->
                <div class="form-group">
                    <label for="email" class="setting-label">{$t('signup.emailLabel')}</label>
                    <div class="input-icon-wrap">
                        <span class="input-icon">
                            <Mail size={18} />
                        </span>
                        <input
                            id="email"
                            type="email"
                            class="custom-input has-icon-left"
                            placeholder="{$t('signup.emailPlaceholder')}"
                            bind:value={email}
                            bind:this={emailRef}
                            onkeydown={(e) => e.key === 'Enter' && focusNext(passwordRef)}
                        />
                    </div>
                </div>

                <!-- Password -->
                <div class="form-group">
                    <label for="password" class="setting-label">{$t('signup.passwordLabel')}</label>
                    <div class="input-icon-wrap">
                        <span class="input-icon">
                            <Lock size={18} />
                        </span>
                        <input
                            id="password"
                            type={showPassword ? "text" : "password"}
                            class="custom-input has-icon-left has-icon-right"
                            placeholder="{$t('signup.passwordPlaceholder')}"
                            bind:value={password}
                            bind:this={passwordRef}
                            onkeydown={(e) => e.key === 'Enter' && !loading && signup()}
                        />
                        <button
                            type="button"
                            class="toggle-password"
                            onclick={() => showPassword = !showPassword}
                            aria-label="Toggle password visibility"
                        >
                            <div class="eye-icon">
                                <span class={showPassword ? "show" : "hide"}>
                                    <Eye size={18} />
                                </span>
                                <span class={showPassword ? "hide" : "show"}>
                                    <EyeClosed size={18} />
                                </span>
                            </div>
                        </button>
                    </div>
                </div>

                {#if message}
                    <p class="message-text">{message}</p>
                {/if}

                <!-- Actions -->
                <div class="form-actions">
                    <button class="action-btn" onclick={() => window.location.href = '/'}>
                        <ArrowLeft size={16} />
                        <span>{$t('signup.back')}</span>
                    </button>
                    <button
                        class="action-btn primary"
                        onclick={signup}
                        disabled={loading}
                    >
                        {#if loading}
                            <span class="spinner"></span>
                            <span>{$t('signup.registering')}</span>
                        {:else}
                            <span>{$t('signup.done')}</span>
                        {/if}
                    </button>
                </div>

            </div>
        </div>
    </div>
</div>

<style>
/* ── Page Layout ────────────────────────────────────────── */
.main-content {
        max-width: 42rem;
        width: 100%;
        margin: 0 auto;
        padding: 0 16px;
    }

    .login-layout {
        display: flex;
        justify-content: center;
    }

    .login-container {
        width: 100%;
        max-width: 28rem;
        padding: 32px 0;
    }

    /* ── Header ─────────────────────────────────────────────── */
    .login-header {
        margin-bottom: 32px;
    }

.page-title {
font-family: var(--font-page-title);
        font-size: 2.25rem;
        font-weight: 400;
        letter-spacing: -0.02em;
        color: var(--color-base-content);
        margin: 0 0 8px;
        line-height: 1.1;
    }

    .section-desc {
        font-size: 14px;
        line-height: 1.45;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        margin: 0;
    }

    /* ── Form ───────────────────────────────────────────────── */
    .form-wrap {
        display: flex;
        flex-direction: column;
        gap: 18px;
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .setting-label {
        font-size: 13px;
        font-weight: 600;
        color: color-mix(in oklch, var(--color-base-content) 80%, transparent);
        padding-left: 2px;
    }

    /* ── Input Wrappers ─────────────────────────────────────── */
    .input-icon-wrap {
        position: relative;
        display: flex;
        align-items: center;
    }

    .custom-input {
        width: 100%;
        height: 44px;
        background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
        border: 1px solid var(--color-base-300);
        border-radius: 10px;
        padding: 0 14px;
        font-size: 14px;
        color: var(--color-base-content);
        transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
        outline: none;
    }

    .custom-input::placeholder {
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
    }

    .custom-input:focus {
        background: var(--color-base-100);
        border-color: var(--color-accent);
        box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
    }

    .custom-input.has-icon-left {
        padding-left: 42px;
    }

    .custom-input.has-icon-right {
        padding-right: 42px;
    }

    /* ── Input Icons ────────────────────────────────────────── */
    .input-icon {
        position: absolute;
        left: 14px;
        color: var(--color-accent);
        display: flex;
        align-items: center;
        pointer-events: none;
        z-index: 2;
    }

    /* ── Password Toggle ────────────────────────────────────── */
    .toggle-password {
        position: absolute;
        right: 12px;
        background: transparent;
        border: none;
        cursor: pointer;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 4px;
        z-index: 2;
        transition: color 150ms;
    }

    .toggle-password:hover {
        color: var(--color-base-content);
    }

    .eye-icon {
        position: relative;
        width: 18px;
        height: 18px;
    }

    .eye-icon :global(svg) {
        position: absolute;
        top: 0;
        left: 0;
        transition: opacity 150ms ease, transform 150ms ease;
    }

    .eye-icon .show {
        opacity: 1;
        transform: scale(1);
    }

    .eye-icon .hide {
        opacity: 0;
        transform: scale(0.6);
    }

    /* ── Message Text ───────────────────────────────────────── */
    .message-text {
        font-size: 13px;
        text-align: center;
        margin: 0;
        padding: 4px 0;
        color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
    }

    /* ── Action Buttons ─────────────────────────────────────── */
    .form-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;
    }

    .action-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 10px 16px;
        border-radius: 10px;
        border: 1px solid var(--color-base-300);
        background: transparent;
        color: var(--color-base-content);
        cursor: pointer;
        font-size: 13px;
        font-weight: 600;
        transition: all 130ms ease;
    }

    .action-btn:hover {
        background: var(--color-base-200);
    }

    .action-btn.primary {
        background: var(--color-accent);
        color: var(--color-base-100);
        border-color: var(--color-accent);
        padding: 10px 24px;
    }

    .action-btn.primary:hover {
        box-shadow: 0 4px 12px color-mix(in oklch, var(--color-accent) 35%, transparent);
        transform: translateY(-1px);
    }

    .action-btn.primary:active {
        transform: scale(0.98);
    }

    .action-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
    }

    .spinner {
        width: 16px;
        height: 16px;
        border: 2px solid color-mix(in oklch, var(--color-base-100) 30%, transparent);
        border-top-color: var(--color-base-100);
        border-radius: 50%;
        animation: spin 0.6s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>