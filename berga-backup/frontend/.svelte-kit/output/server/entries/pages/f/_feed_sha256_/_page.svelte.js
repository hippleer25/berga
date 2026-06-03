import { a as store_get, c as attr, b as attr_class, e as ensure_array_like, u as unsubscribe_stores } from "../../../../chunks/index2.js";
import { p as page } from "../../../../chunks/stores.js";
import { $ as $format } from "../../../../chunks/runtime.js";
/* empty css                                                        */
import { A as Arrow_left } from "../../../../chunks/arrow-left.js";
import { e as escape_html } from "../../../../chunks/context.js";
function skeletonCard($$renderer) {
  $$renderer.push(`<div class="skeleton-card svelte-oomm3y" aria-hidden="true"><div class="sk-row sk-publisher svelte-oomm3y"><div class="sk-circle svelte-oomm3y"></div> <div class="sk-bar svelte-oomm3y" style="width:72px"></div> <div class="sk-dot svelte-oomm3y"></div> <div class="sk-bar svelte-oomm3y" style="width:52px; opacity:.5"></div> <div class="sk-bar sk-ml-auto svelte-oomm3y" style="width:36px; opacity:.4"></div></div> <div class="sk-bar sk-title svelte-oomm3y" style="width:92%"></div> <div class="sk-bar sk-title svelte-oomm3y" style="width:62%; margin-bottom:8px"></div> <div class="sk-bar sk-desc svelte-oomm3y" style="width:100%"></div> <div class="sk-bar sk-desc svelte-oomm3y" style="width:78%; margin-bottom:10px"></div> <div class="sk-row sk-actions svelte-oomm3y"><div class="sk-circle sk-sm svelte-oomm3y"></div> <div class="sk-circle sk-sm svelte-oomm3y"></div></div></div>`);
}
function skeletonHeader($$renderer) {
  $$renderer.push(`<div class="feed-header feed-header--skeleton svelte-oomm3y" aria-hidden="true"><div class="sk-circle fh-icon-sk svelte-oomm3y"></div> <div class="fh-meta svelte-oomm3y"><div class="sk-bar svelte-oomm3y" style="width:160px; height:18px; border-radius:6px"></div> <div class="sk-bar svelte-oomm3y" style="width:100px; height:11px; border-radius:4px; margin-top:8px; opacity:.6"></div> <div class="sk-bar svelte-oomm3y" style="width:220px; height:10px; border-radius:4px; margin-top:10px; opacity:.4"></div></div> <div class="sk-bar fh-btn-sk svelte-oomm3y" style="width:88px; height:34px; border-radius:10px; flex-shrink:0"></div></div>`);
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    store_get($$store_subs ??= {}, "$page", page).params.feed_sha256 ?? "";
    let mode = "recommendations";
    const SKELETON_INITIAL = Array.from({ length: 6 }, (_, i) => i);
    Array.from({ length: 3 }, (_, i) => i);
    $$renderer2.push(`<div class="page-root svelte-oomm3y"><div class="main-content svelte-oomm3y"><header class="top-header svelte-oomm3y"><button class="back-btn svelte-oomm3y"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("feed.back", { default: "Back" }))}>`);
    Arrow_left($$renderer2, { size: 20 });
    $$renderer2.push(`<!----></button></header> `);
    {
      $$renderer2.push("<!--[-->");
      skeletonHeader($$renderer2);
    }
    $$renderer2.push(`<!--]--> <div class="filter-bar svelte-oomm3y"><div class="mode-pill svelte-oomm3y" role="group"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("feed.filterMode", { default: "Feed mode" }))}><button${attr_class("mode-btn svelte-oomm3y", void 0, { "active": mode === "recommendations" })}${attr("aria-pressed", mode === "recommendations")}><span class="svelte-oomm3y">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("feed.forYou"))}</span></button> <button${attr_class("mode-btn svelte-oomm3y", void 0, { "active": mode === "recents" })}${attr("aria-pressed", mode === "recents")}><span class="svelte-oomm3y">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("feed.recents"))}</span></button></div></div> <div class="feed-wrap svelte-oomm3y">`);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<!--[-->`);
      const each_array = ensure_array_like(SKELETON_INITIAL);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        each_array[$$index];
        skeletonCard($$renderer2);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--> <div class="sentinel svelte-oomm3y" aria-hidden="true"></div></div></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
