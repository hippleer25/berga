<script lang="ts">
    import User from "@lucide/svelte/icons/user";
    import UserCircle from "@lucide/svelte/icons/user-circle";
    import Mail from "@lucide/svelte/icons/mail";
    import Lock from "@lucide/svelte/icons/lock";
    import Eye from "@lucide/svelte/icons/eye";
    import EyeClosed from "@lucide/svelte/icons/eye-closed";

    let username = "";
    let password = "";
    let full_name = "";
    let email = "";
    let showPassword = false;

    let message = "";
    let loading = false;

let usernameRef: HTMLInputElement;
let fullNameRef: HTMLInputElement;
let emailRef: HTMLInputElement;
let passwordRef: HTMLInputElement;

function focusNext(nextRef: HTMLInputElement) {
        nextRef?.focus();
    }

    async function signup() {
        loading = true;
        message = "";

        try {
            const response = await fetch(`/api/register`, {
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
                message = data.message;
            } else {
                message = data.message || "Error while signing up";
            }

        } catch (err) {
            message = "Error while signing up";
        }

        loading = false;
    }
</script>

<style>
    .input-icon svg {
        stroke: currentColor !important;
        fill: none !important;
    }
</style>

<div class="min-h-screen flex items-center justify-center bg-base-200 px-6">
    <div class="w-full max-w-lg bg-base-100 rounded-2xl shadow-xl overflow-hidden pt-5">
        <div class="px-10 py-10 max-w-md mx-auto space-y-6">
            <h1 class="text-3xl font-semibold">Sign up</h1>
            <p>You are creating a Berga account</p>

            <div>
                <label for="username" class="font-medium block mb-2">Account</label>
                <div class="relative flex items-center">
                    <span class="input-icon absolute left-3 z-10 text-primary pointer-events-none">
                        <User size={18} color="currentColor" />
                    </span>
                    <input
                        id="username"
                        type="text"
                        placeholder="Enter your username"
                        class="input bg-base-200 border-none w-full pl-10 focus:outline-none"
                        bind:value={username}
                        bind:this={usernameRef}
                        on:keydown={(e) => e.key === 'Enter' && focusNext(fullNameRef)}
                    />
                </div>
            </div>

            <div>
                <label for="full_name" class="font-medium block mb-2">Full name</label>
                <div class="relative flex items-center">
                    <span class="input-icon absolute left-3 z-10 text-primary pointer-events-none">
                        <UserCircle size={18} color="currentColor" />
                    </span>
                    <input
                        id="full_name"
                        type="text"
                        placeholder="Enter your full name"
                        class="input bg-base-200 border-none w-full pl-10 focus:outline-none"
                        bind:value={full_name}
                        bind:this={fullNameRef}
                        on:keydown={(e) => e.key === 'Enter' && focusNext(emailRef)}
                    />
                </div>
            </div>

            <div>
                <label for="email" class="font-medium block mb-2">Email</label>
                <div class="relative flex items-center">
                    <span class="input-icon absolute left-3 z-10 text-primary pointer-events-none">
                        <Mail size={18} color="currentColor" />
                    </span>
                    <input
                        id="email"
                        type="email"
                        placeholder="Enter your email"
                        class="input bg-base-200 border-none w-full pl-10 focus:outline-none"
                        bind:value={email}
                        bind:this={emailRef}
                        on:keydown={(e) => e.key === 'Enter' && focusNext(passwordRef)}
                    />
                </div>
            </div>

            <div>
                <label for="password" class="font-medium block mb-2">Password</label>
                <div class="relative flex items-center">
                    <span class="input-icon absolute left-3 z-10 text-primary pointer-events-none">
                        <Lock size={18} color="currentColor" />
                    </span>
                    <input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Enter your password"
                        class="input bg-base-200 border-none w-full pl-10 pr-10 focus:outline-none"
                        bind:value={password}
                        bind:this={passwordRef}
                        on:keydown={(e) => e.key === 'Enter' && signup()}
                    />
                    <button
                        type="button"
                        class="absolute right-3 z-10 text-primary"
                        on:click={() => showPassword = !showPassword}
                    >
                        {#if showPassword}
                            <EyeClosed size={18} />
                        {:else}
                            <Eye size={18} />
                        {/if}
                    </button>
                </div>
            </div>

            {#if message}
                <p class="text-sm text-center">{message}</p>
            {/if}

            <div class="flex justify-between items-center pt-10">
                <button class="btn bg-base-200 hover:bg-base-300 border-none text-base-content" on:click={() => window.location.href = '/'}>Back</button>
                <button
                    class="btn btn-primary border-none font-bold px-7"
                    on:click={signup}
                    disabled={loading}
                >
                    {#if loading}
                        Registering...
                    {:else}
                        Done
                    {/if}
                </button>
            </div>
        </div>
    </div>
</div>