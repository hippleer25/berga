import { s as spread_props, b as attr_class, c as attr, a as store_get, g as stringify, u as unsubscribe_stores, e as ensure_array_like } from "../../../../chunks/index2.js";
import { p as page } from "../../../../chunks/stores.js";
import "@sveltejs/kit/internal";
import "../../../../chunks/exports.js";
import "../../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../../chunks/state.svelte.js";
import { $ as $format, a as $locale } from "../../../../chunks/runtime.js";
import { g as get } from "../../../../chunks/index.js";
/* empty css                                                        */
import { I as Icon } from "../../../../chunks/Icon.js";
import { H as Heart } from "../../../../chunks/heart.js";
import { T as Thumbs_down } from "../../../../chunks/thumbs-down.js";
import { e as escape_html } from "../../../../chunks/context.js";
import "../../../../chunks/FollowFeedModal.svelte_svelte_type_style_lang.js";
import { S as Search } from "../../../../chunks/search.js";
function Check($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [["path", { "d": "M20 6 9 17l-5-5" }]];
    Icon($$renderer2, spread_props([
      { name: "check" },
      /**
       * @component @name Check
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMjAgNiA5IDE3bC01LTUiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/check
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
function External_link($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M15 3h6v6" }],
      ["path", { "d": "M10 14 21 3" }],
      [
        "path",
        {
          "d": "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "external-link" },
      /**
       * @component @name ExternalLink
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTUgM2g2djYiIC8+CiAgPHBhdGggZD0iTTEwIDE0IDIxIDMiIC8+CiAgPHBhdGggZD0iTTE4IDEzdjZhMiAyIDAgMCAxLTIgMkg1YTIgMiAwIDAgMS0yLTJWOGEyIDIgMCAwIDEgMi0yaDYiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/external-link
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
function PostCard($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let {
      item,
      selectionMode = false,
      selected = false
    } = $$props;
    let liked = item.liked ?? false;
    let disliked = item.disliked ?? false;
    let likeLoading = false;
    let dislikeLoading = false;
    function formatDate(dateStr) {
      const now = /* @__PURE__ */ new Date();
      const date = new Date(dateStr);
      const ms = now.getTime() - date.getTime();
      const min = Math.floor(ms / 6e4);
      const h = Math.floor(ms / 36e5);
      const d = Math.floor(ms / 864e5);
      if (min < 1) return get($format)("postcard.now");
      if (min < 60) return `${min}${get($format)("postcard.minutesShort")}`;
      if (h < 24) return `${h}${get($format)("postcard.hoursShort")}`;
      if (d < 7) return `${d}${get($format)("postcard.daysShort")}`;
      return date.toLocaleDateString(get($locale) ?? "en", {
        day: "2-digit",
        month: "short",
        year: date.getFullYear() !== now.getFullYear() ? "numeric" : void 0
      });
    }
    function getDomain(url) {
      try {
        return new URL(url).hostname.replace("www.", "");
      } catch {
        return url;
      }
    }
    function stripHtml(html) {
      let text = html.replace(/<br\s*[\/]?>/gi, " ");
      text = text.replace(/<[^>]+>/g, "");
      return text.replace(/\s{2,}/g, " ").trim();
    }
    $$renderer2.push(`<article${attr_class("post-card svelte-podw4w", void 0, { "is-selected": selected, "sel-mode": selectionMode })}><div class="sel-col svelte-podw4w"${attr("aria-hidden", !selectionMode)}><button class="sel-circle svelte-podw4w"${attr("aria-label", selected ? store_get($$store_subs ??= {}, "$t", $format)("postcard.deselect") : store_get($$store_subs ??= {}, "$t", $format)("postcard.select"))}${attr("aria-checked", selected)} role="checkbox"${attr("tabindex", selectionMode ? 0 : -1)}>`);
    if (selected) {
      $$renderer2.push("<!--[-->");
      Check($$renderer2, { size: 11, strokeWidth: 3.5 });
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></button></div> <div class="post-content svelte-podw4w"><header class="publisher-row svelte-podw4w">`);
    if (item.feed_icon) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<img${attr("src", item.feed_icon)}${attr("alt", item.feed_title ?? "")} class="feed-icon svelte-podw4w" onerror="this.__e=event"/>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <span class="feed-title svelte-podw4w">${escape_html(item.feed_title ?? getDomain(item.link))}</span> `);
    if (item.author) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<span class="separator svelte-podw4w" aria-hidden="true">·</span> <span class="author svelte-podw4w">${escape_html(item.author)}</span>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <time class="pub-date svelte-podw4w"${attr("datetime", item.pub_date)}>${escape_html(formatDate(item.pub_date))}</time></header> <a${attr("href", `/a/${stringify(item.item_id)}`)} class="title-link svelte-podw4w"${attr("tabindex", selectionMode ? -1 : 0)}>${escape_html(item.title)}</a> `);
    if (item.description) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<p class="description svelte-podw4w">${escape_html(stripHtml(item.description))}</p>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (!selectionMode) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<footer class="actions-row svelte-podw4w"><button${attr("disabled", likeLoading, true)}${attr_class("action-btn svelte-podw4w", void 0, { "action-active": liked })}${attr("aria-label", liked ? store_get($$store_subs ??= {}, "$t", $format)("postcard.unlike") : store_get($$store_subs ??= {}, "$t", $format)("postcard.like"))}${attr("aria-pressed", liked)}>`);
      {
        $$renderer2.push("<!--[!-->");
        Heart($$renderer2, { size: 15, fill: liked ? "currentColor" : "none" });
      }
      $$renderer2.push(`<!--]--></button> <button${attr("disabled", dislikeLoading, true)}${attr_class("action-btn svelte-podw4w", void 0, { "action-active": disliked })}${attr("aria-label", disliked ? store_get($$store_subs ??= {}, "$t", $format)("postcard.undoDislike") : store_get($$store_subs ??= {}, "$t", $format)("postcard.dislike"))}${attr("aria-pressed", disliked)}>`);
      {
        $$renderer2.push("<!--[!-->");
        Thumbs_down($$renderer2, { size: 15, fill: disliked ? "currentColor" : "none" });
      }
      $$renderer2.push(`<!--]--></button> <a${attr("href", item.link)} target="_blank" rel="noopener noreferrer" class="action-btn action-external svelte-podw4w"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("postcard.openOriginal"))}>`);
      External_link($$renderer2, { size: 13 });
      $$renderer2.push(`<!----></a></footer>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div></article>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let activeTab = "articles";
    let searchQuery = decodeURIComponent(store_get($$store_subs ??= {}, "$page", page).params.query ?? "");
    let articleResults = [];
    $$renderer2.push(`<div class="page-root"><div class="main-content svelte-1k32nwf"><header class="page-header svelte-1k32nwf"><form class="search-form svelte-1k32nwf"><div class="search-wrap svelte-1k32nwf"><input class="search-input svelte-1k32nwf" type="search"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("searchtab.placeholder", { default: "Search posts, feeds, or topics..." }))}${attr("value", searchQuery)} autocomplete="off" autocorrect="off" spellcheck="false"/> `);
    Search($$renderer2, { size: 18, class: "search-icon" });
    $$renderer2.push(`<!----></div></form></header> <div class="tab-bar svelte-1k32nwf"><div class="mode-pill svelte-1k32nwf" role="group" aria-label="Search tabs"><button${attr_class("mode-btn svelte-1k32nwf", void 0, { "active": activeTab === "articles" })}${attr("aria-pressed", activeTab === "articles")}><span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("search.articles"))}</span></button> <button${attr_class("mode-btn svelte-1k32nwf", void 0, { "active": activeTab === "feeds" })}${attr("aria-pressed", activeTab === "feeds")}><span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("search.feeds"))}</span></button></div></div> <div class="results-wrap svelte-1k32nwf">`);
    {
      $$renderer2.push("<!--[-->");
      {
        $$renderer2.push("<!--[!-->");
        {
          $$renderer2.push("<!--[!-->");
          if (articleResults.length === 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<p class="state-empty svelte-1k32nwf">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("search.noArticleResults"))} <span class="query-label svelte-1k32nwf">"${escape_html(decodeURIComponent(store_get($$store_subs ??= {}, "$page", page).params.query ?? ""))}"</span></p>`);
          } else {
            $$renderer2.push("<!--[!-->");
            $$renderer2.push(`<p class="results-meta svelte-1k32nwf">${escape_html(articleResults.length)} ${escape_html(articleResults.length !== 1 ? store_get($$store_subs ??= {}, "$t", $format)("search.results") : store_get($$store_subs ??= {}, "$t", $format)("search.result"))} ${escape_html(store_get($$store_subs ??= {}, "$t", $format)("search.for"))} <span class="query-label svelte-1k32nwf">"${escape_html(decodeURIComponent(store_get($$store_subs ??= {}, "$page", page).params.query ?? ""))}"</span></p> <!--[-->`);
            const each_array = ensure_array_like(articleResults);
            for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
              let item = each_array[$$index];
              PostCard($$renderer2, { item });
            }
            $$renderer2.push(`<!--]-->`);
          }
          $$renderer2.push(`<!--]-->`);
        }
        $$renderer2.push(`<!--]-->`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></div></div></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
