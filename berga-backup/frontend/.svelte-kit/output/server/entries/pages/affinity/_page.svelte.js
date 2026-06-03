import { a as store_get, c as attr, b as attr_class, e as ensure_array_like, g as stringify, u as unsubscribe_stores } from "../../../chunks/index2.js";
import { $ as $format } from "../../../chunks/runtime.js";
import { g as get } from "../../../chunks/index.js";
import { S as Sparkles } from "../../../chunks/sparkles.js";
import { S as Search } from "../../../chunks/search.js";
import { A as Arrow_left } from "../../../chunks/arrow-left.js";
import { T as Thumbs_up } from "../../../chunks/thumbs-up.js";
import { T as Thumbs_down } from "../../../chunks/thumbs-down.js";
import { X } from "../../../chunks/x.js";
import { e as escape_html } from "../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let term = "";
    let analyzeStatus = "idle";
    let history = [];
    function affinityLabel(score) {
      if (score >= 0.8) return { text: get($format)("affinity.veryHigh"), cls: "text-success" };
      if (score >= 0.62) return { text: get($format)("affinity.high"), cls: "text-success" };
      if (score >= 0.52) return { text: get($format)("affinity.moderate"), cls: "text-warning" };
      if (score >= 0.42) return { text: get($format)("affinity.low"), cls: "text-error" };
      return { text: get($format)("affinity.veryLow"), cls: "text-error" };
    }
    function pct(score) {
      return Math.round(score * 100);
    }
    $$renderer2.push(`<div class="min-h-screen flex items-center justify-center bg-base-200 px-6 py-10"><div class="w-full max-w-lg space-y-4"><div class="bg-base-100 border border-primary rounded-2xl shadow-lg overflow-hidden"><div class="px-10 py-10 max-w-md mx-auto space-y-6"><div class="space-y-1"><div class="flex items-center gap-2">`);
    Sparkles($$renderer2, { size: 22, class: "text-primary" });
    $$renderer2.push(`<!----> <h1 class="text-3xl font-semibold">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.title"))}</h1></div> <p class="text-sm text-base-content/50">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.subtitle"))}</p></div> <div class="divider my-0"></div> <div class="space-y-2"><span class="font-medium block">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.analyzeLabel"))}</span> <div class="flex gap-2"><input type="text" class="input input-bordered input-sm flex-1 border-[1.5px] rounded-xl"${attr("placeholder", store_get($$store_subs ??= {}, "$t", $format)("affinity.analyzePlaceholder"))}${attr("value", term)}${attr("disabled", analyzeStatus === "loading", true)}/> <button${attr_class(`btn btn-primary btn-sm gap-1.5 rounded-xl px-4 ${stringify("")}`)}${attr("disabled", !term.trim(), true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      Search($$renderer2, { size: 14 });
    }
    $$renderer2.push(`<!--]--> ${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.analyzeBtn"))}</button></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <div class="flex justify-between items-center pt-2"><button class="btn btn-outline bg-base-200 border-[1.5px]">`);
    Arrow_left($$renderer2, { size: 16 });
    $$renderer2.push(`<!----> ${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.back"))}</button></div></div></div> `);
    if (history.length > 0) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="bg-base-100 border border-base-300 rounded-2xl shadow-sm overflow-hidden"><div class="px-6 pt-5 pb-1"><p class="font-medium text-sm text-base-content/60 uppercase tracking-widest">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("affinity.historyTitle"))}</p></div> <ul class="divide-y divide-base-200"><!--[-->`);
      const each_array = ensure_array_like(history);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let entry = each_array[$$index];
        const lbl = affinityLabel(entry.affinity);
        $$renderer2.push(`<li class="flex items-center justify-between px-6 py-3 gap-3 group"><div class="flex items-center gap-2 min-w-0"><button class="text-sm font-medium truncate hover:underline text-left">${escape_html(entry.term)}</button> `);
        if (entry.boostedPositive) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="badge badge-success badge-xs gap-0.5">`);
          Thumbs_up($$renderer2, { size: 9 });
          $$renderer2.push(`<!----> +</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--> `);
        if (entry.boostedNegative) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="badge badge-error badge-xs gap-0.5">`);
          Thumbs_down($$renderer2, { size: 9 });
          $$renderer2.push(`<!----> −</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--></div> <div class="flex items-center gap-3 shrink-0"><span${attr_class(`text-xs font-mono ${stringify(lbl.cls)}`)}>${escape_html(pct(entry.affinity))}%</span> <button class="opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity"${attr("aria-label", store_get($$store_subs ??= {}, "$t", $format)("affinity.removeHistoryAria"))}>`);
        X($$renderer2, { size: 13 });
        $$renderer2.push(`<!----></button></div></li>`);
      }
      $$renderer2.push(`<!--]--></ul></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
