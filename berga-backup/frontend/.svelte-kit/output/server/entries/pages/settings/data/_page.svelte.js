import { s as spread_props, a as store_get, b as attr_class, c as attr, u as unsubscribe_stores } from "../../../../chunks/index2.js";
import { $ as $format } from "../../../../chunks/runtime.js";
import { I as Icon } from "../../../../chunks/Icon.js";
import { R as Refresh_cw } from "../../../../chunks/refresh-cw.js";
import { e as escape_html } from "../../../../chunks/context.js";
function Download($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M12 15V3" }],
      ["path", { "d": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" }],
      ["path", { "d": "m7 10 5 5 5-5" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "download" },
      /**
       * @component @name Download
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTIgMTVWMyIgLz4KICA8cGF0aCBkPSJNMjEgMTV2NGEyIDIgMCAwIDEtMiAySDVhMiAyIDAgMCAxLTItMnYtNCIgLz4KICA8cGF0aCBkPSJtNyAxMCA1IDUgNS01IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/download
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
function Upload($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M12 3v12" }],
      ["path", { "d": "m17 8-5-5-5 5" }],
      ["path", { "d": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "upload" },
      /**
       * @component @name Upload
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTIgM3YxMiIgLz4KICA8cGF0aCBkPSJtMTcgOC01LTUtNSA1IiAvPgogIDxwYXRoIGQ9Ik0yMSAxNXY0YTIgMiAwIDAgMS0yIDJINWEyIDIgMCAwIDEtMi0ydi00IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/upload
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
    let importStatus = "idle";
    let fetchStatus = "idle";
    $$renderer2.push(`<div class="tab-panel svelte-n4bscp"><h2 class="section-title svelte-n4bscp">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.subscriptions"))}</h2> <p class="section-desc svelte-n4bscp">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.subscriptionsDesc"))}</p> <div class="btn-group svelte-n4bscp"><button class="action-btn svelte-n4bscp">`);
    Download($$renderer2, { size: 16 });
    $$renderer2.push(`<!----><span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.exportOpml"))}</span></button> <input type="file" accept=".opml,text/x-opml,application/xml,text/xml" class="hidden-input svelte-n4bscp"/> <button${attr_class("action-btn svelte-n4bscp", void 0, { "success": importStatus === "success" })}${attr("disabled", importStatus === "loading", true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      {
        $$renderer2.push("<!--[!-->");
        Upload($$renderer2, { size: 16 });
        $$renderer2.push(`<!----><span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.importOpml"))}</span>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></button></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <div class="section-divider svelte-n4bscp"></div> <h2 class="section-title svelte-n4bscp">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.fetchNewArticles"))}</h2> <p class="section-desc svelte-n4bscp">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.fetchDesc"))}</p> <button${attr_class("action-btn full-width svelte-n4bscp", void 0, {
      "success": fetchStatus === "success",
      "error": fetchStatus === "error"
    })}${attr("disabled", fetchStatus === "loading", true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      {
        $$renderer2.push("<!--[!-->");
        Refresh_cw($$renderer2, { size: 16 });
        $$renderer2.push(`<!----><span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.fetchArticles"))}</span>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></button> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
