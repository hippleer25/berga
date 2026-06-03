import { r as registerLocaleLoader, i as init } from "./runtime.js";
const NAMESPACES = [
  "navbar",
  "hometab",
  "eventstab",
  "motatab",
  "settings",
  "signup",
  "signin",
  "welcome",
  "followerstab",
  "affinity",
  "search",
  "feed",
  "article",
  "eventscard",
  "followfeedmodal",
  "leftpanel",
  "postcard",
  "topbar",
  "folder",
  "searchtab"
];
const localeFiles = /* @__PURE__ */ Object.assign({ "../locales/de/affinity.json": () => import("./affinity.js"), "../locales/de/article.json": () => import("./article.js"), "../locales/de/eventscard.json": () => import("./eventscard.js"), "../locales/de/eventstab.json": () => import("./eventstab.js"), "../locales/de/feed.json": () => import("./feed.js"), "../locales/de/folder.json": () => import("./folder.js"), "../locales/de/followerstab.json": () => import("./followerstab.js"), "../locales/de/followfeedmodal.json": () => import("./followfeedmodal.js"), "../locales/de/hometab.json": () => import("./hometab.js"), "../locales/de/leftpanel.json": () => import("./leftpanel.js"), "../locales/de/motatab.json": () => import("./motatab.js"), "../locales/de/navbar.json": () => import("./navbar.js"), "../locales/de/postcard.json": () => import("./postcard.js"), "../locales/de/search.json": () => import("./search2.js"), "../locales/de/searchtab.json": () => import("./searchtab.js"), "../locales/de/settings.json": () => import("./settings.js"), "../locales/de/signin.json": () => import("./signin.js"), "../locales/de/signup.json": () => import("./signup.js"), "../locales/de/topbar.json": () => import("./topbar.js"), "../locales/de/welcome.json": () => import("./welcome.js"), "../locales/en/affinity.json": () => import("./affinity2.js"), "../locales/en/article.json": () => import("./article2.js"), "../locales/en/eventscard.json": () => import("./eventscard2.js"), "../locales/en/eventstab.json": () => import("./eventstab2.js"), "../locales/en/feed.json": () => import("./feed2.js"), "../locales/en/folder.json": () => import("./folder2.js"), "../locales/en/followerstab.json": () => import("./followerstab2.js"), "../locales/en/followfeedmodal.json": () => import("./followfeedmodal2.js"), "../locales/en/hometab.json": () => import("./hometab2.js"), "../locales/en/leftpanel.json": () => import("./leftpanel2.js"), "../locales/en/motatab.json": () => import("./motatab2.js"), "../locales/en/navbar.json": () => import("./navbar2.js"), "../locales/en/postcard.json": () => import("./postcard2.js"), "../locales/en/search.json": () => import("./search3.js"), "../locales/en/searchtab.json": () => import("./searchtab2.js"), "../locales/en/settings.json": () => import("./settings2.js"), "../locales/en/signin.json": () => import("./signin2.js"), "../locales/en/signup.json": () => import("./signup2.js"), "../locales/en/topbar.json": () => import("./topbar2.js"), "../locales/en/welcome.json": () => import("./welcome2.js"), "../locales/es/affinity.json": () => import("./affinity3.js"), "../locales/es/article.json": () => import("./article3.js"), "../locales/es/eventscard.json": () => import("./eventscard3.js"), "../locales/es/eventstab.json": () => import("./eventstab3.js"), "../locales/es/feed.json": () => import("./feed3.js"), "../locales/es/folder.json": () => import("./folder3.js"), "../locales/es/followerstab.json": () => import("./followerstab3.js"), "../locales/es/followfeedmodal.json": () => import("./followfeedmodal3.js"), "../locales/es/hometab.json": () => import("./hometab3.js"), "../locales/es/leftpanel.json": () => import("./leftpanel3.js"), "../locales/es/motatab.json": () => import("./motatab3.js"), "../locales/es/navbar.json": () => import("./navbar3.js"), "../locales/es/postcard.json": () => import("./postcard3.js"), "../locales/es/search.json": () => import("./search4.js"), "../locales/es/searchtab.json": () => import("./searchtab3.js"), "../locales/es/settings.json": () => import("./settings3.js"), "../locales/es/signin.json": () => import("./signin3.js"), "../locales/es/signup.json": () => import("./signup3.js"), "../locales/es/topbar.json": () => import("./topbar3.js"), "../locales/es/welcome.json": () => import("./welcome3.js"), "../locales/fr/affinity.json": () => import("./affinity4.js"), "../locales/fr/article.json": () => import("./article4.js"), "../locales/fr/eventscard.json": () => import("./eventscard4.js"), "../locales/fr/eventstab.json": () => import("./eventstab4.js"), "../locales/fr/feed.json": () => import("./feed4.js"), "../locales/fr/folder.json": () => import("./folder4.js"), "../locales/fr/followerstab.json": () => import("./followerstab4.js"), "../locales/fr/followfeedmodal.json": () => import("./followfeedmodal4.js"), "../locales/fr/hometab.json": () => import("./hometab4.js"), "../locales/fr/leftpanel.json": () => import("./leftpanel4.js"), "../locales/fr/motatab.json": () => import("./motatab4.js"), "../locales/fr/navbar.json": () => import("./navbar4.js"), "../locales/fr/postcard.json": () => import("./postcard4.js"), "../locales/fr/search.json": () => import("./search5.js"), "../locales/fr/searchtab.json": () => import("./searchtab4.js"), "../locales/fr/settings.json": () => import("./settings4.js"), "../locales/fr/signin.json": () => import("./signin4.js"), "../locales/fr/signup.json": () => import("./signup4.js"), "../locales/fr/topbar.json": () => import("./topbar4.js"), "../locales/fr/welcome.json": () => import("./welcome4.js"), "../locales/pt/affinity.json": () => import("./affinity5.js"), "../locales/pt/article.json": () => import("./article5.js"), "../locales/pt/eventscard.json": () => import("./eventscard5.js"), "../locales/pt/eventstab.json": () => import("./eventstab5.js"), "../locales/pt/feed.json": () => import("./feed5.js"), "../locales/pt/folder.json": () => import("./folder5.js"), "../locales/pt/followerstab.json": () => import("./followerstab5.js"), "../locales/pt/followfeedmodal.json": () => import("./followfeedmodal5.js"), "../locales/pt/hometab.json": () => import("./hometab5.js"), "../locales/pt/leftpanel.json": () => import("./leftpanel5.js"), "../locales/pt/motatab.json": () => import("./motatab5.js"), "../locales/pt/navbar.json": () => import("./navbar5.js"), "../locales/pt/postcard.json": () => import("./postcard5.js"), "../locales/pt/search.json": () => import("./search6.js"), "../locales/pt/searchtab.json": () => import("./searchtab5.js"), "../locales/pt/settings.json": () => import("./settings5.js"), "../locales/pt/signin.json": () => import("./signin5.js"), "../locales/pt/signup.json": () => import("./signup5.js"), "../locales/pt/topbar.json": () => import("./topbar5.js"), "../locales/pt/welcome.json": () => import("./welcome5.js") });
function flattenObject(obj, prefix = "") {
  return Object.keys(obj).reduce((acc, k) => {
    const pre = prefix.length ? prefix + "." : "";
    if (typeof obj[k] === "object" && obj[k] !== null) {
      Object.assign(acc, flattenObject(obj[k], pre + k));
    } else {
      acc[pre + k] = obj[k];
    }
    return acc;
  }, {});
}
function buildLoader(lang) {
  return async () => {
    const modules = await Promise.all(
      NAMESPACES.map(async (ns) => {
        const path = `../locales/${lang}/${ns}.json`;
        if (!localeFiles[path]) {
          return {};
        }
        const mod = await localeFiles[path]();
        const flat = flattenObject(mod.default || mod);
        const namespaced = {};
        for (const key in flat) {
          namespaced[`${ns}.${key}`] = flat[key];
        }
        return namespaced;
      })
    );
    return Object.assign({}, ...modules);
  };
}
registerLocaleLoader("pt", buildLoader("pt"));
registerLocaleLoader("en", buildLoader("en"));
registerLocaleLoader("es", buildLoader("es"));
registerLocaleLoader("de", buildLoader("de"));
registerLocaleLoader("fr", buildLoader("fr"));
let initialLocale = "en";
init({
  fallbackLocale: "en",
  initialLocale
});
