import "clsx";
import { c as attr, a as store_get, b as attr_class, e as ensure_array_like, u as unsubscribe_stores } from "../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/state.svelte.js";
import { $ as $format } from "../../../chunks/runtime.js";
import "../../../chunks/FollowFeedModal.svelte_svelte_type_style_lang.js";
import { A as Arrow_left } from "../../../chunks/arrow-left.js";
import { S as Search } from "../../../chunks/search.js";
import { R as Refresh_cw } from "../../../chunks/refresh-cw.js";
import { F as Folder_plus } from "../../../chunks/folder-plus.js";
function skeletonRow($$renderer) {
  $$renderer.push(`<div class="sk-row svelte-1ro0zdu" aria-hidden="true"><div class="sk-circle svelte-1ro0zdu"></div> <div class="sk-bar svelte-1ro0zdu" style="width:110px"></div> <div class="sk-bar sk-ml-auto svelte-1ro0zdu" style="width:28px; opacity:.4"></div></div>`);
}
function skeletonHeader($$renderer) {
  $$renderer.push(`<div class="feed-header feed-header--skeleton svelte-1ro0zdu" aria-hidden="true"><div class="sk-circle fh-icon-sk svelte-1ro0zdu"></div> <div class="fh-meta svelte-1ro0zdu"><div class="sk-bar svelte-1ro0zdu" style="width:120px; height:18px; border-radius:6px"></div> <div class="sk-bar svelte-1ro0zdu" style="width:90px; height:11px; border-radius:4px; margin-top:8px; opacity:.6"></div></div> <div class="sk-bar fh-btn-sk svelte-1ro0zdu" style="width:72px; height:34px; border-radius:10px; flex-shrink:0"></div></div>`);
}
function FollowersTab($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let subsData = [];
    let expandedFolders = {};
    let searchQuery = "";
    let isRefreshing = false;
    let groupedFolders = (() => {
      const map = /* @__PURE__ */ new Map();
      for (const feed of subsData) {
        const key = feed.folder?.id ?? "__root__";
        if (!map.has(key)) map.set(key, { folder: feed.folder ?? null, feeds: [], depth: 0 });
        if (!feed._empty_folder) map.get(key).feeds.push(feed);
      }
      const byId = /* @__PURE__ */ new Map();
      for (const group of map.values()) if (group.folder?.id != null) byId.set(group.folder.id, {
        name: group.folder.name,
        parent_id: group.folder.parent_id ?? null
      });
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
      for (const g of groupedFolders) if (g.folder?.id != null) parentOf.set(g.folder.id, g.folder.parent_id ?? null);
      return groupedFolders.filter((group) => {
        let pid = group.folder?.parent_id ?? null;
        while (pid !== null) {
          if (expandedFolders[String(pid)] === false) return false;
          pid = parentOf.get(pid) ?? null;
        }
        return true;
      });
    })();
    (() => {
      if (!searchQuery.trim()) return visibleGroups;
      const q = searchQuery.toLowerCase();
      return visibleGroups.map((group) => ({
        ...group,
        feeds: group.feeds.filter((f) => feedDisplayTitle(f).toLowerCase().includes(q) || (f.url ?? "").toLowerCase().includes(q))
      })).filter((group) => group.feeds.length > 0 || (group.folder?.name ?? "Default").toLowerCase().includes(q));
    })();
    groupedFolders.filter((g) => g.folder !== null).map((g) => g.folder);
    subsData.filter((f) => !f._empty_folder).length;
    function feedDisplayTitle(feed) {
      if (feed.title && feed.title !== "No title") return feed.title;
      try {
        return new URL(feed.url).hostname;
      } catch {
        return feed.url ?? "";
      }
    }
    $$renderer2.push(`<div class="page-root svelte-1ro0zdu"><div class="main-content svelte-1ro0zdu"><header class="top-header svelte-1ro0zdu"><button class="back-btn svelte-1ro0zdu"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("followerstab.back", { default: "Back" }))}>`);
    Arrow_left($$renderer2, { size: 20 });
    $$renderer2.push(`<!----></button></header> `);
    {
      $$renderer2.push("<!--[-->");
      skeletonHeader($$renderer2);
    }
    $$renderer2.push(`<!--]--> <div class="toolbar svelte-1ro0zdu"><div class="search-wrap svelte-1ro0zdu">`);
    Search($$renderer2, { size: 18, class: "search-icon" });
    $$renderer2.push(`<!----> <input class="search-input svelte-1ro0zdu" type="text"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("followerstab.searchPlaceholder"))}${attr("value", searchQuery)}${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("followerstab.searchAria"))}/> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div> <div class="toolbar-actions svelte-1ro0zdu"><button${attr_class("tool-btn svelte-1ro0zdu", void 0, { "spinning": isRefreshing })}${attr("title", store_get($$store_subs ??= {}, "$t", $format)("followerstab.refresh"))}${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("followerstab.refresh"))}${attr("disabled", isRefreshing, true)}>`);
    Refresh_cw($$renderer2, { size: 15, strokeWidth: 2 });
    $$renderer2.push(`<!----></button> <button class="tool-btn svelte-1ro0zdu"${attr("title", store_get($$store_subs ??= {}, "$t", $format)("followerstab.newFolder"))}${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("followerstab.newFolder"))}>`);
    Folder_plus($$renderer2, { size: 15, strokeWidth: 2 });
    $$renderer2.push(`<!----></button></div></div> <div class="tree-body svelte-1ro0zdu">`);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<!--[-->`);
      const each_array = ensure_array_like(Array.from({ length: 8 }));
      for (let i = 0, $$length = each_array.length; i < $$length; i++) {
        each_array[i];
        skeletonRow($$renderer2);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></div></div></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
function _page($$renderer) {
  FollowersTab($$renderer);
}
export {
  _page as default
};
