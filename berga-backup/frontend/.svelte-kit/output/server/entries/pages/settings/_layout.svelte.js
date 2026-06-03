import { s as spread_props, c as attr, a as store_get, e as ensure_array_like, b as attr_class, u as unsubscribe_stores } from "../../../chunks/index2.js";
import { p as page } from "../../../chunks/stores.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/state.svelte.js";
import { $ as $format } from "../../../chunks/runtime.js";
import { A as Arrow_left } from "../../../chunks/arrow-left.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { S as Sparkles } from "../../../chunks/sparkles.js";
import { U as User } from "../../../chunks/user.js";
import { e as escape_html } from "../../../chunks/context.js";
function Database($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["ellipse", { "cx": "12", "cy": "5", "rx": "9", "ry": "3" }],
      ["path", { "d": "M3 5V19A9 3 0 0 0 21 19V5" }],
      ["path", { "d": "M3 12A9 3 0 0 0 21 12" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "database" },
      /**
       * @component @name Database
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8ZWxsaXBzZSBjeD0iMTIiIGN5PSI1IiByeD0iOSIgcnk9IjMiIC8+CiAgPHBhdGggZD0iTTMgNVYxOUE5IDMgMCAwIDAgMjEgMTlWNSIgLz4KICA8cGF0aCBkPSJNMyAxMkE5IDMgMCAwIDAgMjEgMTIiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/database
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
function Palette($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"
        }
      ],
      [
        "circle",
        { "cx": "13.5", "cy": "6.5", "r": ".5", "fill": "currentColor" }
      ],
      [
        "circle",
        {
          "cx": "17.5",
          "cy": "10.5",
          "r": ".5",
          "fill": "currentColor"
        }
      ],
      [
        "circle",
        { "cx": "6.5", "cy": "12.5", "r": ".5", "fill": "currentColor" }
      ],
      [
        "circle",
        { "cx": "8.5", "cy": "7.5", "r": ".5", "fill": "currentColor" }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "palette" },
      /**
       * @component @name Palette
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTIgMjJhMSAxIDAgMCAxIDAtMjAgMTAgOSAwIDAgMSAxMCA5IDUgNSAwIDAgMS01IDVoLTIuMjVhMS43NSAxLjc1IDAgMCAwLTEuNCAyLjhsLjMuNGExLjc1IDEuNzUgMCAwIDEtMS40IDIuOHoiIC8+CiAgPGNpcmNsZSBjeD0iMTMuNSIgY3k9IjYuNSIgcj0iLjUiIGZpbGw9ImN1cnJlbnRDb2xvciIgLz4KICA8Y2lyY2xlIGN4PSIxNy41IiBjeT0iMTAuNSIgcj0iLjUiIGZpbGw9ImN1cnJlbnRDb2xvciIgLz4KICA8Y2lyY2xlIGN4PSI2LjUiIGN5PSIxMi41IiByPSIuNSIgZmlsbD0iY3VycmVudENvbG9yIiAvPgogIDxjaXJjbGUgY3g9IjguNSIgY3k9IjcuNSIgcj0iLjUiIGZpbGw9ImN1cnJlbnRDb2xvciIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/palette
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
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    const { children } = $$props;
    const tabs = [
      {
        key: "appearance",
        href: "/settings/appearance",
        icon: Palette
      },
      { key: "subscriptions", href: "/settings/data", icon: Database },
      { key: "affinity", href: "/settings/affinity", icon: Sparkles },
      { key: "account", href: "/settings/account", icon: User }
    ];
    function isActive(href) {
      return store_get($$store_subs ??= {}, "$page", page).url.pathname === href || store_get($$store_subs ??= {}, "$page", page).url.pathname.startsWith(href + "/");
    }
    $$renderer2.push(`<nav class="mobile-tabs svelte-15zgomd"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("settings.title"))}><!--[-->`);
    const each_array = ensure_array_like(tabs);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let tab = each_array[$$index];
      $$renderer2.push(`<a${attr("href", tab.href)}${attr_class("mobile-tab svelte-15zgomd", void 0, { "active": isActive(tab.href) })}${attr("aria-current", isActive(tab.href) ? "page" : void 0)}><span class="icon-wrap svelte-15zgomd">`);
      $$renderer2.push("<!---->");
      tab.icon?.($$renderer2, { size: 22, strokeWidth: isActive(tab.href) ? 2.2 : 1.8 });
      $$renderer2.push(`<!----></span> <span class="tab-label svelte-15zgomd">${escape_html(store_get($$store_subs ??= {}, "$t", $format)(`settings.${tab.key === "subscriptions" ? "subscriptions" : tab.key}`))}</span></a>`);
    }
    $$renderer2.push(`<!--]--></nav> <aside class="sidebar svelte-15zgomd"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("settings.title"))}><div class="sidebar-inner svelte-15zgomd"><div class="brand svelte-15zgomd"></div> <nav class="sidebar-nav svelte-15zgomd"><a href="/home" class="sidebar-item svelte-15zgomd"${attr("title", store_get($$store_subs ??= {}, "$t", $format)("settings.back"))}>`);
    Arrow_left($$renderer2, { size: 20, strokeWidth: 1.6 });
    $$renderer2.push(`<!----> <span class="s-label svelte-15zgomd">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.back"))}</span></a> <div class="sidebar-divider svelte-15zgomd"></div> <!--[-->`);
    const each_array_1 = ensure_array_like(tabs);
    for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
      let tab = each_array_1[$$index_1];
      $$renderer2.push(`<a${attr("href", tab.href)}${attr_class("sidebar-item svelte-15zgomd", void 0, { "active": isActive(tab.href) })}${attr("aria-current", isActive(tab.href) ? "page" : void 0)}${attr("title", store_get($$store_subs ??= {}, "$t", $format)(`settings.${tab.key === "subscriptions" ? "subscriptions" : tab.key}`))}>`);
      $$renderer2.push("<!---->");
      tab.icon?.($$renderer2, { size: 20, strokeWidth: isActive(tab.href) ? 2.2 : 1.6 });
      $$renderer2.push(`<!----> <span class="s-label svelte-15zgomd">${escape_html(store_get($$store_subs ??= {}, "$t", $format)(`settings.${tab.key === "subscriptions" ? "subscriptions" : tab.key}`))}</span></a>`);
    }
    $$renderer2.push(`<!--]--></nav></div></aside> <div class="settings-content svelte-15zgomd">`);
    children($$renderer2);
    $$renderer2.push(`<!----></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _layout as default
};
