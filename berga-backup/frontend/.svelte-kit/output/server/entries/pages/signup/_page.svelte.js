import { a as store_get, c as attr, b as attr_class, k as clsx, u as unsubscribe_stores } from "../../../chunks/index2.js";
import { $ as $format } from "../../../chunks/runtime.js";
import { U as User } from "../../../chunks/user.js";
import { C as Circle_user } from "../../../chunks/circle-user.js";
import { M as Mail, L as Lock, E as Eye } from "../../../chunks/mail.js";
import { E as Eye_closed } from "../../../chunks/eye-closed.js";
import { A as Arrow_left } from "../../../chunks/arrow-left.js";
import { e as escape_html } from "../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let username = "";
    let password = "";
    let full_name = "";
    let email = "";
    let loading = false;
    $$renderer2.push(`<div class="page-root page-root--centered"><div class="main-content login-layout svelte-kmqcod"><div class="login-container svelte-kmqcod"><div class="login-header svelte-kmqcod"><h1 class="page-title svelte-kmqcod">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signup.title"))}</h1> <p class="section-desc svelte-kmqcod">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signup.subtitle"))}</p></div> <div class="form-wrap svelte-kmqcod"><div class="form-group svelte-kmqcod"><label for="username" class="setting-label svelte-kmqcod">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signup.accountLabel"))}</label> <div class="input-icon-wrap svelte-kmqcod"><span class="input-icon svelte-kmqcod">`);
    User($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span> <input id="username" type="text" class="custom-input has-icon-left svelte-kmqcod"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("signup.accountPlaceholder"))}${attr("value", username)}/></div></div> <div class="form-group svelte-kmqcod"><label for="full_name" class="setting-label svelte-kmqcod">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signup.fullNameLabel"))}</label> <div class="input-icon-wrap svelte-kmqcod"><span class="input-icon svelte-kmqcod">`);
    Circle_user($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span> <input id="full_name" type="text" class="custom-input has-icon-left svelte-kmqcod"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("signup.fullNamePlaceholder"))}${attr("value", full_name)}/></div></div> <div class="form-group svelte-kmqcod"><label for="email" class="setting-label svelte-kmqcod">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signup.emailLabel"))}</label> <div class="input-icon-wrap svelte-kmqcod"><span class="input-icon svelte-kmqcod">`);
    Mail($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span> <input id="email" type="email" class="custom-input has-icon-left svelte-kmqcod"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("signup.emailPlaceholder"))}${attr("value", email)}/></div></div> <div class="form-group svelte-kmqcod"><label for="password" class="setting-label svelte-kmqcod">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signup.passwordLabel"))}</label> <div class="input-icon-wrap svelte-kmqcod"><span class="input-icon svelte-kmqcod">`);
    Lock($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span> <input id="password"${attr("type", "password")} class="custom-input has-icon-left has-icon-right svelte-kmqcod"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("signup.passwordPlaceholder"))}${attr("value", password)}/> <button type="button" class="toggle-password svelte-kmqcod" aria-label="Toggle password visibility"><div class="eye-icon svelte-kmqcod"><span${attr_class(clsx("hide"), "svelte-kmqcod")}>`);
    Eye($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span> <span${attr_class(clsx("show"), "svelte-kmqcod")}>`);
    Eye_closed($$renderer2, { size: 18 });
    $$renderer2.push(`<!----></span></div></button></div></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <div class="form-actions svelte-kmqcod"><button class="action-btn svelte-kmqcod">`);
    Arrow_left($$renderer2, { size: 16 });
    $$renderer2.push(`<!----> <span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signup.back"))}</span></button> <button class="action-btn primary svelte-kmqcod"${attr("disabled", loading, true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("signup.done"))}</span>`);
    }
    $$renderer2.push(`<!--]--></button></div></div></div></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
