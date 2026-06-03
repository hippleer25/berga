import { s as spread_props, h as head, b as attr_class, c as attr, a as store_get, u as unsubscribe_stores } from "../../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../../chunks/exports.js";
import "../../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../../chunks/state.svelte.js";
import { $ as $format } from "../../../../chunks/runtime.js";
import { A as Arrow_left } from "../../../../chunks/arrow-left.js";
import { I as Icon } from "../../../../chunks/Icon.js";
import { H as Heart } from "../../../../chunks/heart.js";
import { T as Thumbs_down } from "../../../../chunks/thumbs-down.js";
import { e as escape_html } from "../../../../chunks/context.js";
function Bookmark($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "M17 3a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "bookmark" },
      /**
       * @component @name Bookmark
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTcgM2EyIDIgMCAwIDEgMiAydjE1YTEgMSAwIDAgMS0xLjQ5Ni44NjhsLTQuNTEyLTIuNTc4YTIgMiAwIDAgMC0xLjk4NCAwbC00LjUxMiAyLjU3OEExIDEgMCAwIDEgNSAyMFY1YTIgMiAwIDAgMSAyLTJ6IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/bookmark
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
function Globe($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["circle", { "cx": "12", "cy": "12", "r": "10" }],
      [
        "path",
        { "d": "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" }
      ],
      ["path", { "d": "M2 12h20" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "globe" },
      /**
       * @component @name Globe
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIgLz4KICA8cGF0aCBkPSJNMTIgMmExNC41IDE0LjUgMCAwIDAgMCAyMCAxNC41IDE0LjUgMCAwIDAgMC0yMCIgLz4KICA8cGF0aCBkPSJNMiAxMmgyMCIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/globe
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
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let loading = true;
    let liked = false;
    let disliked = false;
    let saved = false;
    let likeLoading = false;
    let dislikeLoading = false;
    let saveLoading = false;
    let webView = false;
    head("12837ym", $$renderer2, ($$renderer3) => {
      {
        $$renderer3.push("<!--[!-->");
      }
      $$renderer3.push(`<!--]-->`);
    });
    $$renderer2.push(`<div${attr_class("reader-page svelte-12837ym", void 0, { "web-mode": webView })}><header class="top-bar-wrap svelte-12837ym"><div class="top-bar svelte-12837ym"><button class="ghost-btn back-btn svelte-12837ym"${attr("title", store_get($$store_subs ??= {}, "$t", $format)("article.backToFeed"))}>`);
    Arrow_left($$renderer2, { size: 18 });
    $$renderer2.push(`<!----> <span class="back-label svelte-12837ym">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("article.backToFeed"))}</span></button> <div class="source-info svelte-12837ym">`);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <span class="source-name svelte-12837ym">${escape_html("")}</span></div> <div class="top-actions svelte-12837ym"><button${attr_class("ghost-btn svelte-12837ym", void 0, { "active-view": webView })}${attr("title", store_get($$store_subs ??= {}, "$t", $format)("article.viewOriginalPage"))}${attr("disabled", loading, true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      Globe($$renderer2, { size: 16 });
    }
    $$renderer2.push(`<!--]--></button> <div class="divider svelte-12837ym"></div> <button${attr_class("ghost-btn svelte-12837ym", void 0, { "active-action": liked })}${attr("title", store_get($$store_subs ??= {}, "$t", $format)("article.like"))}${attr("disabled", likeLoading, true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      Heart($$renderer2, { size: 16, fill: "none" });
    }
    $$renderer2.push(`<!--]--></button> <button${attr_class("ghost-btn svelte-12837ym", void 0, { "active-action": disliked })}${attr("title", store_get($$store_subs ??= {}, "$t", $format)("article.dislike"))}${attr("disabled", dislikeLoading, true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      Thumbs_down($$renderer2, { size: 16, fill: "none" });
    }
    $$renderer2.push(`<!--]--></button> <button${attr_class("ghost-btn svelte-12837ym", void 0, { "active-save": saved })}${attr("title", store_get($$store_subs ??= {}, "$t", $format)("article.save"))}${attr("disabled", saveLoading, true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      Bookmark($$renderer2, { size: 16, fill: "none" });
    }
    $$renderer2.push(`<!--]--></button> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div></div></header> `);
    {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<main class="reader-scroll svelte-12837ym"><div class="reader-content svelte-12837ym">`);
      {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="state-loading svelte-12837ym"><span class="loading loading-spinner loading-lg svelte-12837ym"></span></div>`);
      }
      $$renderer2.push(`<!--]--></div></main>`);
    }
    $$renderer2.push(`<!--]--></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
