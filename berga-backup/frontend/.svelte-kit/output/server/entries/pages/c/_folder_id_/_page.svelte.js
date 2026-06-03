import { s as spread_props, a as store_get, c as attr, b as attr_class, e as ensure_array_like, u as unsubscribe_stores } from "../../../../chunks/index2.js";
import { p as page } from "../../../../chunks/stores.js";
import { $ as $format } from "../../../../chunks/runtime.js";
/* empty css                                                        */
import { A as Arrow_left } from "../../../../chunks/arrow-left.js";
import { S as Sparkles } from "../../../../chunks/sparkles.js";
import { I as Icon } from "../../../../chunks/Icon.js";
import { e as escape_html } from "../../../../chunks/context.js";
function Clock($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["circle", { "cx": "12", "cy": "12", "r": "10" }],
      ["path", { "d": "M12 6v6l4 2" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "clock" },
      /**
       * @component @name Clock
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIgLz4KICA8cGF0aCBkPSJNMTIgNnY2bDQgMiIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/clock
       * @see https://lucide.dev/guide/packages/lucide-svelte - Documentation
       *
       * @param {Object} props - Lucide icons props and any valid SVG attribute
       * @returns {FunctionalComponent} Svelte component
       *
       */
      props,
      {
        iconNode,
        children: ($$renderer3) => {
          props.children?.($$renderer3);
          $$renderer3.push(`<!---->`);
        },
        $$slots: { default: true }
      }
    ]));
  });
}
function skeletonCard($$renderer) {
  $$renderer.push(`<div class="skeleton-card svelte-58kw0v" aria-hidden="true"><div class="sk-row sk-publisher svelte-58kw0v"><div class="sk-circle svelte-58kw0v"></div> <div class="sk-bar svelte-58kw0v" style="width:72px"></div> <div class="sk-dot svelte-58kw0v"></div> <div class="sk-bar svelte-58kw0v" style="width:52px; opacity:.5"></div> <div class="sk-bar sk-ml-auto svelte-58kw0v" style="width:36px; opacity:.4"></div></div> <div class="sk-bar sk-title svelte-58kw0v" style="width:92%"></div> <div class="sk-bar sk-title svelte-58kw0v" style="width:62%; margin-bottom:8px"></div> <div class="sk-bar sk-desc svelte-58kw0v" style="width:100%"></div> <div class="sk-bar sk-desc svelte-58kw0v" style="width:78%; margin-bottom:10px"></div> <div class="sk-row sk-actions svelte-58kw0v"><div class="sk-circle sk-sm svelte-58kw0v"></div> <div class="sk-circle sk-sm svelte-58kw0v"></div></div></div>`);
}
function skeletonHeader($$renderer) {
  $$renderer.push(`<div class="folder-header folder-header--skeleton svelte-58kw0v" aria-hidden="true"><div class="sk-circle fh-icon-sk svelte-58kw0v"></div> <div class="fh-meta svelte-58kw0v"><div class="sk-bar svelte-58kw0v" style="width:140px; height:18px; border-radius:6px"></div> <div class="sk-bar svelte-58kw0v" style="width:100px; height:11px; border-radius:4px; margin-top:8px; opacity:.6"></div> <div class="sk-bar svelte-58kw0v" style="width:180px; height:10px; border-radius:4px; margin-top:10px; opacity:.4"></div></div></div>`);
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    store_get($$store_subs ??= {}, "$page", page).params.folder_id ?? "";
    let mode = "recommendations";
    const SKELETON_INITIAL = Array.from({ length: 6 }, (_, i) => i);
    Array.from({ length: 3 }, (_, i) => i);
    $$renderer2.push(`<div class="page-root svelte-58kw0v"><div class="main-content svelte-58kw0v"><header class="top-header svelte-58kw0v"><button class="back-btn svelte-58kw0v"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("folder.back", { default: "Back" }))}>`);
    Arrow_left($$renderer2, { size: 20 });
    $$renderer2.push(`<!----></button></header> `);
    {
      $$renderer2.push("<!--[-->");
      skeletonHeader($$renderer2);
    }
    $$renderer2.push(`<!--]--> <div class="filter-bar svelte-58kw0v"><div class="mode-pill svelte-58kw0v" role="group"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("folder.filterMode", { default: "Feed mode" }))}><button${attr_class("mode-btn svelte-58kw0v", void 0, { "active": mode === "recommendations" })}${attr("aria-pressed", mode === "recommendations")}>`);
    Sparkles($$renderer2, { size: 12, strokeWidth: 2.2 });
    $$renderer2.push(`<!----> <span class="svelte-58kw0v">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("folder.forYou", { default: "For You" }))}</span></button> <button${attr_class("mode-btn svelte-58kw0v", void 0, { "active": mode === "recents" })}${attr("aria-pressed", mode === "recents")}>`);
    Clock($$renderer2, { size: 12, strokeWidth: 2.2 });
    $$renderer2.push(`<!----> <span class="svelte-58kw0v">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("folder.recents", { default: "Recent" }))}</span></button></div></div> <div class="feed-wrap svelte-58kw0v">`);
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
    $$renderer2.push(`<!--]--> <div class="sentinel svelte-58kw0v" aria-hidden="true"></div></div></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
