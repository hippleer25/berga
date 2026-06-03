import { a as store_get, c as attr, b as attr_class, k as clsx, u as unsubscribe_stores } from "../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/state.svelte.js";
import { $ as $format } from "../../../chunks/runtime.js";
import { M as Mail, L as Lock, E as Eye } from "../../../chunks/mail.js";
import { U as User } from "../../../chunks/user.js";
import { E as Eye_closed } from "../../../chunks/eye-closed.js";
import { A as Arrow_left } from "../../../chunks/arrow-left.js";
import { e as escape_html } from "../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let identifier = "";
    let password = "";
    let loading = false;
    let isEmail = identifier.includes("@");
    $$renderer2.push(`<div class="page-root page-root--centered"><div class="main-content login-layout svelte-1x05zx6"><div class="login-container svelte-1x05zx6"><div class="login-header svelte-1x05zx6"><h1 class="page-title svelte-1x05zx6">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signin.title"))}</h1> <p class="section-desc svelte-1x05zx6">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signin.subtitle"))}</p></div> <div class="form-wrap svelte-1x05zx6"><div class="form-group svelte-1x05zx6"><label for="identifier" class="setting-label svelte-1x05zx6">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signin.identifierLabel"))}</label> <div class="input-icon-wrap svelte-1x05zx6"><span class="input-icon svelte-1x05zx6">`);
    if (isEmail) {
      $$renderer2.push("<!--[-->");
      Mail($$renderer2, { size: 18 });
    } else {
      $$renderer2.push("<!--[!-->");
      User($$renderer2, { size: 18 });
    }
    $$renderer2.push(`<!--]--></span> <input id="identifier" type="text" class="custom-input has-icon-left svelte-1x05zx6"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("signin.identifierPlaceholder"))}${attr("value", identifier)}/></div></div> <div class="form-group svelte-1x05zx6"><label for="password" class="setting-label svelte-1x05zx6">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signin.passwordLabel"))}</label> <div class="input-icon-wrap svelte-1x05zx6"><span class="input-icon svelte-1x05zx6">`);
    Lock($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span> <input id="password"${attr("type", "password")} class="custom-input has-icon-left has-icon-right svelte-1x05zx6"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("signin.passwordPlaceholder"))}${attr("value", password)}/> <button type="button" class="toggle-password svelte-1x05zx6" aria-label="Toggle password visibility"><div class="eye-icon svelte-1x05zx6"><span${attr_class(clsx("hide"), "svelte-1x05zx6")}>`);
    Eye($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span> <span${attr_class(clsx("show"), "svelte-1x05zx6")}>`);
    Eye_closed($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span></div></button></div></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <div class="form-actions svelte-1x05zx6"><button class="action-btn svelte-1x05zx6">`);
    Arrow_left($$renderer2, { size: 16 });
    $$renderer2.push(`<!----> <span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signin.back"))}</span></button> <button class="action-btn primary svelte-1x05zx6"${attr("disabled", loading, true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signin.loginBtn"))}</span>`);
    }
    $$renderer2.push(`<!--]--></button></div></div></div></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
