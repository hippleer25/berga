import { s as spread_props, a as store_get, b as attr_class, c as attr, e as ensure_array_like, u as unsubscribe_stores, d as attr_style, f as bind_props, g as stringify, h as head, j as store_set } from "../../chunks/index2.js";
import { p as page } from "../../chunks/stores.js";
import { w as writable } from "../../chunks/index.js";
import { $ as $format } from "../../chunks/runtime.js";
import { I as Icon } from "../../chunks/Icon.js";
import { S as Sparkles } from "../../chunks/sparkles.js";
import { e as escape_html } from "../../chunks/context.js";
import "@sveltejs/kit/internal";
import "../../chunks/exports.js";
import "../../chunks/utils.js";
import "clsx";
import "@sveltejs/kit/internal/server";
import "../../chunks/state.svelte.js";
import { F as Folder_plus } from "../../chunks/folder-plus.js";
import { X } from "../../chunks/x.js";
import { C as Chevron_down } from "../../chunks/chevron-down.js";
function Chevron_right($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [["path", { "d": "m9 18 6-6-6-6" }]];
    Icon($$renderer2, spread_props([
      { name: "chevron-right" },
      /**
       * @component @name ChevronRight
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJtOSAxOCA2LTYtNi02IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/chevron-right
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
function Ellipsis($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["circle", { "cx": "12", "cy": "12", "r": "1" }],
      ["circle", { "cx": "19", "cy": "12", "r": "1" }],
      ["circle", { "cx": "5", "cy": "12", "r": "1" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "ellipsis" },
      /**
       * @component @name Ellipsis
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxIiAvPgogIDxjaXJjbGUgY3g9IjE5IiBjeT0iMTIiIHI9IjEiIC8+CiAgPGNpcmNsZSBjeD0iNSIgY3k9IjEyIiByPSIxIiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/ellipsis
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
function Folder_open($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "folder-open" },
      /**
       * @component @name FolderOpen
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJtNiAxNCAxLjUtMi45QTIgMiAwIDAgMSA5LjI0IDEwSDIwYTIgMiAwIDAgMSAxLjk0IDIuNWwtMS41NCA2YTIgMiAwIDAgMS0xLjk1IDEuNUg0YTIgMiAwIDAgMS0yLTJWNWEyIDIgMCAwIDEgMi0yaDMuOWEyIDIgMCAwIDEgMS42OS45bC44MSAxLjJhMiAyIDAgMCAwIDEuNjcuOUgxOGEyIDIgMCAwIDEgMiAydjIiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/folder-open
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
function Folder($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "folder" },
      /**
       * @component @name Folder
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMjAgMjBhMiAyIDAgMCAwIDItMlY4YTIgMiAwIDAgMC0yLTJoLTcuOWEyIDIgMCAwIDEtMS42OS0uOUw5LjYgMy45QTIgMiAwIDAgMCA3LjkzIDNINGEyIDIgMCAwIDAtMiAydjEzYTIgMiAwIDAgMCAyIDJaIiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/folder
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
function House($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        { "d": "M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8" }
      ],
      [
        "path",
        {
          "d": "M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "house" },
      /**
       * @component @name House
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTUgMjF2LThhMSAxIDAgMCAwLTEtMWgtNGExIDEgMCAwIDAtMSAxdjgiIC8+CiAgPHBhdGggZD0iTTMgMTBhMiAyIDAgMCAxIC43MDktMS41MjhsNy02YTIgMiAwIDAgMSAyLjU4MiAwbDcgNkEyIDIgMCAwIDEgMjEgMTB2OWEyIDIgMCAwIDEtMiAySDVhMiAyIDAgMCAxLTItMnoiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/house
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
function Newspaper($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M15 18h-5" }],
      ["path", { "d": "M18 14h-8" }],
      [
        "path",
        {
          "d": "M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-4 0v-9a2 2 0 0 1 2-2h2"
        }
      ],
      [
        "rect",
        { "width": "8", "height": "4", "x": "10", "y": "6", "rx": "1" }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "newspaper" },
      /**
       * @component @name Newspaper
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTUgMThoLTUiIC8+CiAgPHBhdGggZD0iTTE4IDE0aC04IiAvPgogIDxwYXRoIGQ9Ik00IDIyaDE2YTIgMiAwIDAgMCAyLTJWNGEyIDIgMCAwIDAtMi0ySDhhMiAyIDAgMCAwLTIgMnYxNmEyIDIgMCAwIDEtNCAwdi05YTIgMiAwIDAgMSAyLTJoMiIgLz4KICA8cmVjdCB3aWR0aD0iOCIgaGVpZ2h0PSI0IiB4PSIxMCIgeT0iNiIgcng9IjEiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/newspaper
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
function Rss($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M4 11a9 9 0 0 1 9 9" }],
      ["path", { "d": "M4 4a16 16 0 0 1 16 16" }],
      ["circle", { "cx": "5", "cy": "19", "r": "1" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "rss" },
      /**
       * @component @name Rss
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNNCAxMWE5IDkgMCAwIDEgOSA5IiAvPgogIDxwYXRoIGQ9Ik00IDRhMTYgMTYgMCAwIDEgMTYgMTYiIC8+CiAgPGNpcmNsZSBjeD0iNSIgY3k9IjE5IiByPSIxIiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/rss
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
const activeTabIdx = writable(0);
const navVisible = writable(true);
function NavBar($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    const tabs = [
      { key: "followers", href: "/followers", icon: Rss },
      { key: "home", href: "/home", icon: House },
      { key: "events", href: "/events", icon: Newspaper },
      { key: "mota", href: "/mota", icon: Sparkles }
    ];
    const tabIdx = store_get($$store_subs ??= {}, "$activeTabIdx", activeTabIdx);
    $$renderer2.push(`<nav${attr_class("mobile-nav svelte-q971rm", void 0, {
      "nav-hidden": !store_get($$store_subs ??= {}, "$navVisible", navVisible)
    })}${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("navbar.mainNav"))}><!--[-->`);
    const each_array = ensure_array_like(tabs);
    for (let i = 0, $$length = each_array.length; i < $$length; i++) {
      let tab = each_array[i];
      const active = tabIdx === i;
      $$renderer2.push(`<a${attr("href", tab.href)}${attr_class("nav-item svelte-q971rm", void 0, { "active": active })}${attr("aria-current", active ? "page" : void 0)}><span class="icon-wrap svelte-q971rm">`);
      $$renderer2.push("<!---->");
      tab.icon?.($$renderer2, { size: 22, strokeWidth: active ? 2.2 : 1.8 });
      $$renderer2.push(`<!----></span> <span class="nav-label svelte-q971rm">${escape_html(store_get($$store_subs ??= {}, "$t", $format)(`navbar.${tab.key}`))}</span></a>`);
    }
    $$renderer2.push(`<!--]--></nav> <aside class="sidebar svelte-q971rm"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("navbar.mainNav"))}><div class="sidebar-inner svelte-q971rm"><div class="brand svelte-q971rm"></div> <nav class="sidebar-nav svelte-q971rm"><!--[-->`);
    const each_array_1 = ensure_array_like(tabs);
    for (let i = 0, $$length = each_array_1.length; i < $$length; i++) {
      let tab = each_array_1[i];
      const active = tabIdx === i;
      $$renderer2.push(`<a${attr("href", tab.href)}${attr_class("sidebar-item svelte-q971rm", void 0, { "active": active })}${attr("aria-current", active ? "page" : void 0)}${attr("title", store_get($$store_subs ??= {}, "$t", $format)(`navbar.${tab.key}`))}>`);
      $$renderer2.push("<!---->");
      tab.icon?.($$renderer2, { size: 20, strokeWidth: active ? 2.2 : 1.6 });
      $$renderer2.push(`<!----> <span class="s-label svelte-q971rm">${escape_html(store_get($$store_subs ??= {}, "$t", $format)(`navbar.${tab.key}`))}</span></a>`);
    }
    $$renderer2.push(`<!--]--></nav></div></aside>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
function PageTrack($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const TABS = ["/followers", "/home", "/events", "/mota"];
    const N = TABS.length;
    let tabComponents = Array(N).fill(null);
    let tabReady = Array(N).fill(false);
    let activeIdx = 0;
    $$renderer2.push(`<div class="viewport svelte-di86pq"><div class="track svelte-di86pq"><div${attr_class("panel svelte-di86pq", void 0, { "panel-active": activeIdx === 0 })}>`);
    if (tabReady[0] && tabComponents[0]) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push("<!---->");
      tabComponents[0]?.($$renderer2, {});
      $$renderer2.push(`<!---->`);
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<div class="tab-loader svelte-di86pq"></div>`);
    }
    $$renderer2.push(`<!--]--></div> <div${attr_class("panel svelte-di86pq", void 0, { "panel-active": activeIdx === 1 })}>`);
    if (tabReady[1] && tabComponents[1]) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push("<!---->");
      tabComponents[1]?.($$renderer2, {});
      $$renderer2.push(`<!---->`);
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<div class="tab-loader svelte-di86pq"></div>`);
    }
    $$renderer2.push(`<!--]--></div> <div${attr_class("panel svelte-di86pq", void 0, { "panel-active": activeIdx === 2 })}>`);
    if (tabReady[2] && tabComponents[2]) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push("<!---->");
      tabComponents[2]?.($$renderer2, {});
      $$renderer2.push(`<!---->`);
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<div class="tab-loader svelte-di86pq"></div>`);
    }
    $$renderer2.push(`<!--]--></div> <div${attr_class("panel svelte-di86pq", void 0, { "panel-active": activeIdx === 3 })}>`);
    if (tabReady[3] && tabComponents[3]) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push("<!---->");
      tabComponents[3]?.($$renderer2, {});
      $$renderer2.push(`<!---->`);
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<div class="tab-loader svelte-di86pq"></div>`);
    }
    $$renderer2.push(`<!--]--></div></div></div>`);
  });
}
function LeftPanel($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let { open = false } = $$props;
    let subsData = [];
    let expandedFolders = {};
    let dragOverKey = null;
    function isExpanded(key) {
      return expandedFolders[String(key)] !== false;
    }
    let groupedFolders = (() => {
      const map = /* @__PURE__ */ new Map();
      for (const feed of subsData) {
        const key = feed.folder?.id ?? "__root__";
        if (!map.has(key)) {
          map.set(key, { folder: feed.folder ?? null, feeds: [], depth: 0 });
        }
        if (!feed._empty_folder) {
          map.get(key).feeds.push(feed);
        }
      }
      const byId = /* @__PURE__ */ new Map();
      for (const group of map.values()) {
        if (group.folder?.id != null) {
          byId.set(group.folder.id, {
            name: group.folder.name,
            parent_id: group.folder.parent_id ?? null
          });
        }
      }
      const memo = /* @__PURE__ */ new Map();
      function getPath(id) {
        if (id === null) return [];
        if (memo.has(id)) return memo.get(id);
        const f = byId.get(id);
        if (!f) {
          memo.set(id, []);
          return [];
        }
        const path = [...getPath(f.parent_id), f.name];
        memo.set(id, path);
        return path;
      }
      const withPath = [];
      for (const group of map.values()) {
        const path = group.folder ? getPath(group.folder.id) : [];
        group.depth = Math.max(0, path.length - 1);
        withPath.push({ group, sortKey: path.join("\0") || "\0" });
      }
      return withPath.sort((a, b) => a.sortKey.localeCompare(b.sortKey)).map(({ group }) => group);
    })();
    let visibleGroups = (() => {
      const parentOf = /* @__PURE__ */ new Map();
      for (const g of groupedFolders) {
        if (g.folder?.id != null) parentOf.set(g.folder.id, g.folder.parent_id ?? null);
      }
      return groupedFolders.filter((group) => {
        let pid = group.folder?.parent_id ?? null;
        while (pid !== null) {
          if (expandedFolders[String(pid)] === false) return false;
          pid = parentOf.get(pid) ?? null;
        }
        return true;
      });
    })();
    function feedDisplayTitle(feed) {
      if (feed.title && feed.title !== "No title") return feed.title;
      try {
        return new URL(feed.url).hostname;
      } catch {
        return feed.url ?? "";
      }
    }
    if (open) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="drawer-backdrop svelte-1tblt3l" aria-hidden="true"></div> <aside class="drawer-panel svelte-1tblt3l"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("leftpanel.title"))}><div class="drawer-header svelte-1tblt3l"><div class="drawer-title-row svelte-1tblt3l">`);
      Rss($$renderer2, { size: 15, strokeWidth: 2.5 });
      $$renderer2.push(`<!----> <span class="drawer-title svelte-1tblt3l">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("leftpanel.title"))}</span></div> <div class="header-actions svelte-1tblt3l"><button class="icon-btn svelte-1tblt3l"${attr("title", store_get($$store_subs ??= {}, "$t", $format)("leftpanel.newFolder"))}${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("leftpanel.newFolder"))}>`);
      Folder_plus($$renderer2, { size: 16, strokeWidth: 2 });
      $$renderer2.push(`<!----></button> <button class="icon-btn svelte-1tblt3l"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("leftpanel.closeDrawer"))}>`);
      X($$renderer2, { size: 18, strokeWidth: 2 });
      $$renderer2.push(`<!----></button></div></div> <div class="drawer-body svelte-1tblt3l">`);
      {
        $$renderer2.push("<!--[!-->");
        {
          $$renderer2.push("<!--[!-->");
          if (groupedFolders.length === 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<p class="subs-empty svelte-1tblt3l">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("leftpanel.noSubscriptions"))}</p>`);
          } else {
            $$renderer2.push("<!--[!-->");
            $$renderer2.push(`<!--[-->`);
            const each_array = ensure_array_like(visibleGroups);
            for (let $$index_1 = 0, $$length = each_array.length; $$index_1 < $$length; $$index_1++) {
              let group = each_array[$$index_1];
              const groupKey = group.folder?.id ?? "__root__";
              const folderExpanded = isExpanded(groupKey);
              const isOver = dragOverKey === groupKey;
              const indent = group.depth * 14;
              $$renderer2.push(`<div${attr_class("folder-block svelte-1tblt3l", void 0, { "drag-over": isOver })}><div class="folder-row svelte-1tblt3l"${attr_style(`padding-left: ${stringify(10 + indent)}px; --indent: ${stringify(indent)}px;`)}${attr("draggable", !!group.folder)} role="button" tabindex="0"${attr("aria-expanded", folderExpanded)}><span class="folder-chevron svelte-1tblt3l">`);
              if (folderExpanded) {
                $$renderer2.push("<!--[-->");
                Chevron_down($$renderer2, { size: 14, strokeWidth: 2.5 });
              } else {
                $$renderer2.push("<!--[!-->");
                Chevron_right($$renderer2, { size: 14, strokeWidth: 2.5 });
              }
              $$renderer2.push(`<!--]--></span> <span class="folder-icon svelte-1tblt3l">`);
              if (folderExpanded) {
                $$renderer2.push("<!--[-->");
                Folder_open($$renderer2, { size: 13, strokeWidth: 2 });
              } else {
                $$renderer2.push("<!--[!-->");
                Folder($$renderer2, { size: 13, strokeWidth: 2 });
              }
              $$renderer2.push(`<!--]--></span> <span class="folder-name svelte-1tblt3l">${escape_html(group.folder?.name ?? store_get($$store_subs ??= {}, "$t", $format)("leftpanel.defaultFolder"))}</span> <span class="folder-badge svelte-1tblt3l">${escape_html(group.feeds.length)}</span> <button class="more-btn svelte-1tblt3l"${attr("title", store_get($$store_subs ??= {}, "$t", $format)("leftpanel.options"))}${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("leftpanel.folderOptions"))}>`);
              Ellipsis($$renderer2, { size: 14, strokeWidth: 2 });
              $$renderer2.push(`<!----></button></div> `);
              if (folderExpanded && group.feeds.length > 0) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<ul class="feed-list svelte-1tblt3l"><!--[-->`);
                const each_array_1 = ensure_array_like(group.feeds);
                for (let $$index = 0, $$length2 = each_array_1.length; $$index < $$length2; $$index++) {
                  let feed = each_array_1[$$index];
                  $$renderer2.push(`<li class="feed-row svelte-1tblt3l"${attr_style(`padding-left: ${stringify(28 + indent)}px;`)}${attr("draggable", true)} role="button" tabindex="0"${attr("title", feedDisplayTitle(feed))}><span class="drag-handle svelte-1tblt3l" aria-hidden="true">⠿</span> `);
                  if (feed.icon) {
                    $$renderer2.push("<!--[-->");
                    $$renderer2.push(`<img${attr("src", feed.icon)} alt="" class="feed-favicon svelte-1tblt3l" onerror="this.__e=event"/>`);
                  } else {
                    $$renderer2.push("<!--[!-->");
                    $$renderer2.push(`<span class="feed-favicon-fallback svelte-1tblt3l">`);
                    Rss($$renderer2, { size: 11 });
                    $$renderer2.push(`<!----></span>`);
                  }
                  $$renderer2.push(`<!--]--> <span class="feed-label svelte-1tblt3l">${escape_html(feedDisplayTitle(feed))}</span> <button class="more-btn svelte-1tblt3l"${attr("title", store_get($$store_subs ??= {}, "$t", $format)("leftpanel.options"))}${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("leftpanel.feedOptions"))}>`);
                  Ellipsis($$renderer2, { size: 14, strokeWidth: 2 });
                  $$renderer2.push(`<!----></button></li>`);
                }
                $$renderer2.push(`<!--]--></ul>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div>`);
            }
            $$renderer2.push(`<!--]-->`);
          }
          $$renderer2.push(`<!--]-->`);
        }
        $$renderer2.push(`<!--]-->`);
      }
      $$renderer2.push(`<!--]--></div></aside> `);
      {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> `);
      {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]-->`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
    bind_props($$props, { open });
  });
}
const drawerOpen = writable(false);
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    const { children } = $$props;
    const TAB_ROUTES = ["/followers", "/home", "/events", "/mota"];
    const isTab = TAB_ROUTES.some((r) => store_get($$store_subs ??= {}, "$page", page).url.pathname === r || store_get($$store_subs ??= {}, "$page", page).url.pathname.startsWith(r + "/"));
    let $$settled = true;
    let $$inner_renderer;
    function $$render_inner($$renderer3) {
      head("12qhfyh", $$renderer3, ($$renderer4) => {
        $$renderer4.title(($$renderer5) => {
          $$renderer5.push(`<title>Berga</title>`);
        });
        $$renderer4.push(`<link rel="icon" href="/landing.jpg"/>`);
      });
      if (isTab) {
        $$renderer3.push("<!--[-->");
        LeftPanel($$renderer3, {
          get open() {
            return store_get($$store_subs ??= {}, "$drawerOpen", drawerOpen);
          },
          set open($$value) {
            store_set(drawerOpen, $$value);
            $$settled = false;
          }
        });
        $$renderer3.push(`<!----> `);
        NavBar($$renderer3);
        $$renderer3.push(`<!----> `);
        PageTrack($$renderer3);
        $$renderer3.push(`<!---->`);
      } else {
        $$renderer3.push("<!--[!-->");
        children($$renderer3);
        $$renderer3.push(`<!---->`);
      }
      $$renderer3.push(`<!--]-->`);
    }
    do {
      $$settled = true;
      $$inner_renderer = $$renderer2.copy();
      $$render_inner($$inner_renderer);
    } while (!$$settled);
    $$renderer2.subsume($$inner_renderer);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _layout as default
};
