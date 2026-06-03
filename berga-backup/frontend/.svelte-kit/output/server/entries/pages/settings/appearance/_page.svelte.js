import { a as store_get, b as attr_class, e as ensure_array_like, d as attr_style, g as stringify, c as attr, u as unsubscribe_stores } from "../../../../chunks/index2.js";
import { $ as $format, a as $locale } from "../../../../chunks/runtime.js";
import "../../../../chunks/index3.js";
import { C as Chevron_down } from "../../../../chunks/chevron-down.js";
import { e as escape_html } from "../../../../chunks/context.js";
const FONT_LIST = [
  { name: "Manrope", category: "sans-serif" },
  { name: "Figtree", category: "sans-serif" },
  { name: "Barlow", category: "sans-serif" },
  { name: "Karla", category: "sans-serif" },
  { name: "PT Sans", category: "sans-serif" },
  { name: "PT Serif", category: "serif" },
  { name: "Inter", category: "sans-serif" },
  { name: "Gloock", category: "serif" },
  { name: "Playfair Display", category: "serif" },
  { name: "Vollkorn", category: "serif" },
  { name: "Newsreader", category: "serif" }
];
const FONT_LABELS = {
  "Manrope": "Manrope",
  "Figtree": "Figtree",
  "Barlow": "Barlow",
  "Karla": "Karla",
  "PT Sans": "PT Sans",
  "PT Serif": "PT Serif",
  "Inter": "Inter",
  "Gloock": "Gloock",
  "Playfair Display": "Playfair",
  "Vollkorn": "Vollkorn",
  "Newsreader": "Newsreader"
};
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    const LOCALE_LABELS = {
      pt: "Português",
      en: "English",
      es: "Español",
      de: "Deutsch",
      fr: "Français"
    };
    const fontCategories = [
      { key: "page-title", labelKey: "settings.pageTitleFont" },
      { key: "post-title", labelKey: "settings.postTitleFont" },
      { key: "article-body", labelKey: "settings.articleBodyFont" },
      { key: "ui", labelKey: "settings.uiFont" }
    ];
    let activeFonts = {
      "page-title": "Newsreader",
      "post-title": "PT Serif",
      "article-body": "Inter",
      "ui": "Inter"
    };
    let activeTheme = "berga";
    let langDropdownOpen = false;
    let openFontDropdown = null;
    let customCss = "";
    let cssSaveStatus = "idle";
    $$renderer2.push(`<div class="tab-panel svelte-zvqmnz"><h2 class="section-title svelte-zvqmnz">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.appearance"))}</h2> <div class="setting-row svelte-zvqmnz"><span class="setting-label svelte-zvqmnz">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.language"))}</span> <div class="picker-wrap svelte-zvqmnz"><button class="setting-btn svelte-zvqmnz"><span>${escape_html(store_get($$store_subs ??= {}, "$locale", $locale) ? LOCALE_LABELS[store_get($$store_subs ??= {}, "$locale", $locale)] ?? store_get($$store_subs ??= {}, "$locale", $locale) : "")}</span> <span${attr_class("chevron-icon svelte-zvqmnz", void 0, { "rotated": langDropdownOpen })}>`);
    Chevron_down($$renderer2, { size: 14 });
    $$renderer2.push(`<!----></span></button></div></div> <div class="setting-row svelte-zvqmnz"><div class="setting-text svelte-zvqmnz"><span class="setting-label svelte-zvqmnz">${escape_html(
      store_get($$store_subs ??= {}, "$t", $format)("settings.lightMode")
    )}</span></div> <button${attr_class("pill-toggle svelte-zvqmnz", void 0, { "on": activeTheme === "berga-black" })}><div class="pill-thumb svelte-zvqmnz"></div></button></div> <!--[-->`);
    const each_array = ensure_array_like(fontCategories);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let cat = each_array[$$index];
      $$renderer2.push(`<div class="setting-row svelte-zvqmnz"><span class="setting-label svelte-zvqmnz">${escape_html(store_get($$store_subs ??= {}, "$t", $format)(cat.labelKey))}</span> <div class="picker-wrap svelte-zvqmnz"><button class="setting-btn svelte-zvqmnz"><span${attr_style(`font-family: '${stringify(activeFonts[cat.key])}', ${stringify(FONT_LIST.find((f) => f.name === activeFonts[cat.key])?.category ?? "sans-serif")};`)}>${escape_html(FONT_LABELS[activeFonts[cat.key]] ?? activeFonts[cat.key])}</span> <span${attr_class("chevron-icon svelte-zvqmnz", void 0, { "rotated": openFontDropdown === cat.key })}>`);
      Chevron_down($$renderer2, { size: 14 });
      $$renderer2.push(`<!----></span></button></div></div>`);
    }
    $$renderer2.push(`<!--]--> <div class="setting-block svelte-zvqmnz"><span class="setting-label svelte-zvqmnz">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.customCss"))}</span> <p class="section-desc svelte-zvqmnz">${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.customCssDesc"))}</p> <textarea class="css-editor svelte-zvqmnz" placeholder="/* Your custom CSS here */
.page-root { ... }" spellcheck="false" rows="8">`);
    const $$body = escape_html(customCss);
    if ($$body) {
      $$renderer2.push(`${$$body}`);
    }
    $$renderer2.push(`</textarea> <div class="css-actions svelte-zvqmnz"><button class="action-btn accent svelte-zvqmnz"${attr("disabled", cssSaveStatus === "saving", true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push(`<span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.saveCss"))}</span>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></button> <button class="action-btn svelte-zvqmnz"${attr("disabled", !customCss.trim(), true)}><span>${escape_html(store_get($$store_subs ??= {}, "$t", $format)("settings.resetCss"))}</span></button></div></div></div> `);
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
export {
  _page as default
};
