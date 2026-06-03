import { a as store_get, c as attr, e as ensure_array_like, b as attr_class, g as stringify, u as unsubscribe_stores } from "../../../../chunks/index2.js";
import { $ as $format } from "../../../../chunks/runtime.js";
import { g as get } from "../../../../chunks/index.js";
import { S as Sparkles } from "../../../../chunks/sparkles.js";
import { S as Search } from "../../../../chunks/search.js";
import { T as Thumbs_up } from "../../../../chunks/thumbs-up.js";
import { T as Thumbs_down } from "../../../../chunks/thumbs-down.js";
import { X } from "../../../../chunks/x.js";
import { e as escape_html } from "../../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let term = "";
    let analyzeStatus = "idle";
    let history = [];
    function affinityLabel(score) {
      if (score >= 0.8) return {
        text: get($format)("affinity.veryHigh"),
        color: "var(--color-success)"
      };
      if (score >= 0.62) return { text: get($format)("affinity.high"), color: "var(--color-success)" };
      if (score >= 0.52) return {
        text: get($format)("affinity.moderate"),
        color: "var(--color-warning)"
      };
      if (score >= 0.42) return { text: get($format)("affinity.low"), color: "var(--color-error)" };
      return {
        text: get($format)("affinity.veryLow"),
        color: "var(--color-error)"
      };
    }
    function pct(score) {
      return Math.round(score * 100);
    }
    $$renderer2.push(`<div class="tab-panel svelte-1reolnl"><div class="affinity-header svelte-1reolnl">`);
    Sparkles($$renderer2, { size: 18, class: "affinity-icon" });
    $$renderer2.push(`<!----> <div><h2 class="section-title svelte-1reolnl">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.title"))}</h2> <p class="section-desc tight svelte-1reolnl">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.subtitle"))}</p></div></div> <div class="affinity-search-row svelte-1reolnl"><div class="search-wrap-sm svelte-1reolnl"><input type="text" class="affinity-input svelte-1reolnl"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("affinity.analyzePlaceholder"))}${attr("value", term)}${attr("disabled", analyzeStatus === "loading", true)}/> `);
    Search($$renderer2, { size: 16, class: "search-icon-sm" });
    $$renderer2.push(`<!----></div> <button class="action-btn accent svelte-1reolnl"${attr("disabled", !term.trim(), true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      Search($$renderer2, { size: 14 });
    }
    $$renderer2.push(`<!--]--> <span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.analyzeBtn"))}</span></button></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (history.length > 0) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="history-section svelte-1reolnl"><p class="history-title svelte-1reolnl">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.historyTitle"))}</p> <div class="history-list svelte-1reolnl"><!--[-->`);
      const each_array = ensure_array_like(history);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let entry = each_array[$$index];
        const lbl = affinityLabel(entry.affinity);
        $$renderer2.push(`<div class="history-item svelte-1reolnl"><div class="history-left svelte-1reolnl"><button class="history-term svelte-1reolnl">${escape_html(entry.term)}</button> `);
        if (entry.boostedPositive) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="mini-badge positive svelte-1reolnl">`);
          Thumbs_up($$renderer2, { size: 8 });
          $$renderer2.push(`<!----> +</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--> `);
        if (entry.boostedNegative) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="mini-badge negative svelte-1reolnl">`);
          Thumbs_down($$renderer2, { size: 8 });
          $$renderer2.push(`<!----> −</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--></div> <div class="history-right svelte-1reolnl"><span${attr_class(`history-score affinity-${stringify(lbl.text.toLowerCase().replace(" ", "-"))}`, "svelte-1reolnl")}>${escape_html(pct(entry.affinity))}%</span> <button class="history-remove svelte-1reolnl"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("affinity.removeHistoryAria"))}>`);
        X($$renderer2, { size: 13 });
        $$renderer2.push(`<!----></button></div></div>`);
      }
      $$renderer2.push(`<!--]--></div></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
