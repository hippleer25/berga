export const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set(["background-mobile.png","berga.png","favicon.ico","fonts/Barlow/Barlow-Black.ttf","fonts/Barlow/Barlow-BlackItalic.ttf","fonts/Barlow/Barlow-Bold.ttf","fonts/Barlow/Barlow-BoldItalic.ttf","fonts/Barlow/Barlow-ExtraBold.ttf","fonts/Barlow/Barlow-ExtraBoldItalic.ttf","fonts/Barlow/Barlow-ExtraLight.ttf","fonts/Barlow/Barlow-ExtraLightItalic.ttf","fonts/Barlow/Barlow-Italic.ttf","fonts/Barlow/Barlow-Light.ttf","fonts/Barlow/Barlow-LightItalic.ttf","fonts/Barlow/Barlow-Medium.ttf","fonts/Barlow/Barlow-MediumItalic.ttf","fonts/Barlow/Barlow-Regular.ttf","fonts/Barlow/Barlow-SemiBold.ttf","fonts/Barlow/Barlow-SemiBoldItalic.ttf","fonts/Barlow/Barlow-Thin.ttf","fonts/Barlow/Barlow-ThinItalic.ttf","fonts/Barlow/OFL.txt","fonts/Figtree/Figtree-Italic-VariableFont_wght.ttf","fonts/Figtree/Figtree-VariableFont_wght.ttf","fonts/Figtree/OFL.txt","fonts/Figtree/README.txt","fonts/Figtree/static/Figtree-Black.ttf","fonts/Figtree/static/Figtree-BlackItalic.ttf","fonts/Figtree/static/Figtree-Bold.ttf","fonts/Figtree/static/Figtree-BoldItalic.ttf","fonts/Figtree/static/Figtree-ExtraBold.ttf","fonts/Figtree/static/Figtree-ExtraBoldItalic.ttf","fonts/Figtree/static/Figtree-Italic.ttf","fonts/Figtree/static/Figtree-Light.ttf","fonts/Figtree/static/Figtree-LightItalic.ttf","fonts/Figtree/static/Figtree-Medium.ttf","fonts/Figtree/static/Figtree-MediumItalic.ttf","fonts/Figtree/static/Figtree-Regular.ttf","fonts/Figtree/static/Figtree-SemiBold.ttf","fonts/Figtree/static/Figtree-SemiBoldItalic.ttf","fonts/Gloock/Gloock-Regular.ttf","fonts/Gloock/OFL.txt","fonts/Inter/Inter-Italic-VariableFont_opsz,wght.ttf","fonts/Inter/Inter-VariableFont_opsz,wght.ttf","fonts/Inter/OFL.txt","fonts/Inter/README.txt","fonts/Inter/static/Inter_18pt-Black.ttf","fonts/Inter/static/Inter_18pt-BlackItalic.ttf","fonts/Inter/static/Inter_18pt-Bold.ttf","fonts/Inter/static/Inter_18pt-BoldItalic.ttf","fonts/Inter/static/Inter_18pt-ExtraBold.ttf","fonts/Inter/static/Inter_18pt-ExtraBoldItalic.ttf","fonts/Inter/static/Inter_18pt-ExtraLight.ttf","fonts/Inter/static/Inter_18pt-ExtraLightItalic.ttf","fonts/Inter/static/Inter_18pt-Italic.ttf","fonts/Inter/static/Inter_18pt-Light.ttf","fonts/Inter/static/Inter_18pt-LightItalic.ttf","fonts/Inter/static/Inter_18pt-Medium.ttf","fonts/Inter/static/Inter_18pt-MediumItalic.ttf","fonts/Inter/static/Inter_18pt-Regular.ttf","fonts/Inter/static/Inter_18pt-SemiBold.ttf","fonts/Inter/static/Inter_18pt-SemiBoldItalic.ttf","fonts/Inter/static/Inter_18pt-Thin.ttf","fonts/Inter/static/Inter_18pt-ThinItalic.ttf","fonts/Inter/static/Inter_24pt-Black.ttf","fonts/Inter/static/Inter_24pt-BlackItalic.ttf","fonts/Inter/static/Inter_24pt-Bold.ttf","fonts/Inter/static/Inter_24pt-BoldItalic.ttf","fonts/Inter/static/Inter_24pt-ExtraBold.ttf","fonts/Inter/static/Inter_24pt-ExtraBoldItalic.ttf","fonts/Inter/static/Inter_24pt-ExtraLight.ttf","fonts/Inter/static/Inter_24pt-ExtraLightItalic.ttf","fonts/Inter/static/Inter_24pt-Italic.ttf","fonts/Inter/static/Inter_24pt-Light.ttf","fonts/Inter/static/Inter_24pt-LightItalic.ttf","fonts/Inter/static/Inter_24pt-Medium.ttf","fonts/Inter/static/Inter_24pt-MediumItalic.ttf","fonts/Inter/static/Inter_24pt-Regular.ttf","fonts/Inter/static/Inter_24pt-SemiBold.ttf","fonts/Inter/static/Inter_24pt-SemiBoldItalic.ttf","fonts/Inter/static/Inter_24pt-Thin.ttf","fonts/Inter/static/Inter_24pt-ThinItalic.ttf","fonts/Inter/static/Inter_28pt-Black.ttf","fonts/Inter/static/Inter_28pt-BlackItalic.ttf","fonts/Inter/static/Inter_28pt-Bold.ttf","fonts/Inter/static/Inter_28pt-BoldItalic.ttf","fonts/Inter/static/Inter_28pt-ExtraBold.ttf","fonts/Inter/static/Inter_28pt-ExtraBoldItalic.ttf","fonts/Inter/static/Inter_28pt-ExtraLight.ttf","fonts/Inter/static/Inter_28pt-ExtraLightItalic.ttf","fonts/Inter/static/Inter_28pt-Italic.ttf","fonts/Inter/static/Inter_28pt-Light.ttf","fonts/Inter/static/Inter_28pt-LightItalic.ttf","fonts/Inter/static/Inter_28pt-Medium.ttf","fonts/Inter/static/Inter_28pt-MediumItalic.ttf","fonts/Inter/static/Inter_28pt-Regular.ttf","fonts/Inter/static/Inter_28pt-SemiBold.ttf","fonts/Inter/static/Inter_28pt-SemiBoldItalic.ttf","fonts/Inter/static/Inter_28pt-Thin.ttf","fonts/Inter/static/Inter_28pt-ThinItalic.ttf","fonts/Karla/Karla-Italic-VariableFont_wght.ttf","fonts/Karla/Karla-VariableFont_wght.ttf","fonts/Karla/OFL.txt","fonts/Karla/README.txt","fonts/Karla/static/Karla-Bold.ttf","fonts/Karla/static/Karla-BoldItalic.ttf","fonts/Karla/static/Karla-ExtraBold.ttf","fonts/Karla/static/Karla-ExtraBoldItalic.ttf","fonts/Karla/static/Karla-ExtraLight.ttf","fonts/Karla/static/Karla-ExtraLightItalic.ttf","fonts/Karla/static/Karla-Italic.ttf","fonts/Karla/static/Karla-Light.ttf","fonts/Karla/static/Karla-LightItalic.ttf","fonts/Karla/static/Karla-Medium.ttf","fonts/Karla/static/Karla-MediumItalic.ttf","fonts/Karla/static/Karla-Regular.ttf","fonts/Karla/static/Karla-SemiBold.ttf","fonts/Karla/static/Karla-SemiBoldItalic.ttf","fonts/Manrope/Manrope-VariableFont_wght.ttf","fonts/Manrope/OFL.txt","fonts/Manrope/README.txt","fonts/Manrope/static/Manrope-Bold.ttf","fonts/Manrope/static/Manrope-ExtraBold.ttf","fonts/Manrope/static/Manrope-ExtraLight.ttf","fonts/Manrope/static/Manrope-Light.ttf","fonts/Manrope/static/Manrope-Medium.ttf","fonts/Manrope/static/Manrope-Regular.ttf","fonts/Manrope/static/Manrope-SemiBold.ttf","fonts/Newsreader/Newsreader-Italic-VariableFont_opsz,wght.ttf","fonts/Newsreader/Newsreader-VariableFont_opsz,wght.ttf","fonts/Newsreader/OFL.txt","fonts/Newsreader/README.txt","fonts/Newsreader/static/Newsreader_14pt-Bold.ttf","fonts/Newsreader/static/Newsreader_14pt-BoldItalic.ttf","fonts/Newsreader/static/Newsreader_14pt-ExtraBold.ttf","fonts/Newsreader/static/Newsreader_14pt-ExtraBoldItalic.ttf","fonts/Newsreader/static/Newsreader_14pt-ExtraLight.ttf","fonts/Newsreader/static/Newsreader_14pt-ExtraLightItalic.ttf","fonts/Newsreader/static/Newsreader_14pt-Italic.ttf","fonts/Newsreader/static/Newsreader_14pt-Light.ttf","fonts/Newsreader/static/Newsreader_14pt-LightItalic.ttf","fonts/Newsreader/static/Newsreader_14pt-Medium.ttf","fonts/Newsreader/static/Newsreader_14pt-MediumItalic.ttf","fonts/Newsreader/static/Newsreader_14pt-Regular.ttf","fonts/Newsreader/static/Newsreader_14pt-SemiBold.ttf","fonts/Newsreader/static/Newsreader_14pt-SemiBoldItalic.ttf","fonts/Newsreader/static/Newsreader_24pt-Bold.ttf","fonts/Newsreader/static/Newsreader_24pt-BoldItalic.ttf","fonts/Newsreader/static/Newsreader_24pt-ExtraBold.ttf","fonts/Newsreader/static/Newsreader_24pt-ExtraBoldItalic.ttf","fonts/Newsreader/static/Newsreader_24pt-ExtraLight.ttf","fonts/Newsreader/static/Newsreader_24pt-ExtraLightItalic.ttf","fonts/Newsreader/static/Newsreader_24pt-Italic.ttf","fonts/Newsreader/static/Newsreader_24pt-Light.ttf","fonts/Newsreader/static/Newsreader_24pt-LightItalic.ttf","fonts/Newsreader/static/Newsreader_24pt-Medium.ttf","fonts/Newsreader/static/Newsreader_24pt-MediumItalic.ttf","fonts/Newsreader/static/Newsreader_24pt-Regular.ttf","fonts/Newsreader/static/Newsreader_24pt-SemiBold.ttf","fonts/Newsreader/static/Newsreader_24pt-SemiBoldItalic.ttf","fonts/Newsreader/static/Newsreader_36pt-Bold.ttf","fonts/Newsreader/static/Newsreader_36pt-BoldItalic.ttf","fonts/Newsreader/static/Newsreader_36pt-ExtraBold.ttf","fonts/Newsreader/static/Newsreader_36pt-ExtraBoldItalic.ttf","fonts/Newsreader/static/Newsreader_36pt-ExtraLight.ttf","fonts/Newsreader/static/Newsreader_36pt-ExtraLightItalic.ttf","fonts/Newsreader/static/Newsreader_36pt-Italic.ttf","fonts/Newsreader/static/Newsreader_36pt-Light.ttf","fonts/Newsreader/static/Newsreader_36pt-LightItalic.ttf","fonts/Newsreader/static/Newsreader_36pt-Medium.ttf","fonts/Newsreader/static/Newsreader_36pt-MediumItalic.ttf","fonts/Newsreader/static/Newsreader_36pt-Regular.ttf","fonts/Newsreader/static/Newsreader_36pt-SemiBold.ttf","fonts/Newsreader/static/Newsreader_36pt-SemiBoldItalic.ttf","fonts/Newsreader/static/Newsreader_60pt-Bold.ttf","fonts/Newsreader/static/Newsreader_60pt-BoldItalic.ttf","fonts/Newsreader/static/Newsreader_60pt-ExtraBold.ttf","fonts/Newsreader/static/Newsreader_60pt-ExtraBoldItalic.ttf","fonts/Newsreader/static/Newsreader_60pt-ExtraLight.ttf","fonts/Newsreader/static/Newsreader_60pt-ExtraLightItalic.ttf","fonts/Newsreader/static/Newsreader_60pt-Italic.ttf","fonts/Newsreader/static/Newsreader_60pt-Light.ttf","fonts/Newsreader/static/Newsreader_60pt-LightItalic.ttf","fonts/Newsreader/static/Newsreader_60pt-Medium.ttf","fonts/Newsreader/static/Newsreader_60pt-MediumItalic.ttf","fonts/Newsreader/static/Newsreader_60pt-Regular.ttf","fonts/Newsreader/static/Newsreader_60pt-SemiBold.ttf","fonts/Newsreader/static/Newsreader_60pt-SemiBoldItalic.ttf","fonts/Newsreader/static/Newsreader_9pt-Bold.ttf","fonts/Newsreader/static/Newsreader_9pt-BoldItalic.ttf","fonts/Newsreader/static/Newsreader_9pt-ExtraBold.ttf","fonts/Newsreader/static/Newsreader_9pt-ExtraBoldItalic.ttf","fonts/Newsreader/static/Newsreader_9pt-ExtraLight.ttf","fonts/Newsreader/static/Newsreader_9pt-ExtraLightItalic.ttf","fonts/Newsreader/static/Newsreader_9pt-Italic.ttf","fonts/Newsreader/static/Newsreader_9pt-Light.ttf","fonts/Newsreader/static/Newsreader_9pt-LightItalic.ttf","fonts/Newsreader/static/Newsreader_9pt-Medium.ttf","fonts/Newsreader/static/Newsreader_9pt-MediumItalic.ttf","fonts/Newsreader/static/Newsreader_9pt-Regular.ttf","fonts/Newsreader/static/Newsreader_9pt-SemiBold.ttf","fonts/Newsreader/static/Newsreader_9pt-SemiBoldItalic.ttf","fonts/PT_Sans/OFL.txt","fonts/PT_Sans/PTSans-Bold.ttf","fonts/PT_Sans/PTSans-BoldItalic.ttf","fonts/PT_Sans/PTSans-Italic.ttf","fonts/PT_Sans/PTSans-Regular.ttf","fonts/PT_Serif/OFL.txt","fonts/PT_Serif/PTSerif-Bold.ttf","fonts/PT_Serif/PTSerif-BoldItalic.ttf","fonts/PT_Serif/PTSerif-Italic.ttf","fonts/PT_Serif/PTSerif-Regular.ttf","fonts/Playfair_Display/OFL.txt","fonts/Playfair_Display/PlayfairDisplay-Italic-VariableFont_wght.ttf","fonts/Playfair_Display/PlayfairDisplay-VariableFont_wght.ttf","fonts/Playfair_Display/README.txt","fonts/Playfair_Display/static/PlayfairDisplay-Black.ttf","fonts/Playfair_Display/static/PlayfairDisplay-BlackItalic.ttf","fonts/Playfair_Display/static/PlayfairDisplay-Bold.ttf","fonts/Playfair_Display/static/PlayfairDisplay-BoldItalic.ttf","fonts/Playfair_Display/static/PlayfairDisplay-ExtraBold.ttf","fonts/Playfair_Display/static/PlayfairDisplay-ExtraBoldItalic.ttf","fonts/Playfair_Display/static/PlayfairDisplay-Italic.ttf","fonts/Playfair_Display/static/PlayfairDisplay-Medium.ttf","fonts/Playfair_Display/static/PlayfairDisplay-MediumItalic.ttf","fonts/Playfair_Display/static/PlayfairDisplay-Regular.ttf","fonts/Playfair_Display/static/PlayfairDisplay-SemiBold.ttf","fonts/Playfair_Display/static/PlayfairDisplay-SemiBoldItalic.ttf","fonts/Vollkorn/OFL.txt","fonts/Vollkorn/README.txt","fonts/Vollkorn/Vollkorn-Italic-VariableFont_wght.ttf","fonts/Vollkorn/Vollkorn-VariableFont_wght.ttf","fonts/Vollkorn/static/Vollkorn-Black.ttf","fonts/Vollkorn/static/Vollkorn-BlackItalic.ttf","fonts/Vollkorn/static/Vollkorn-Bold.ttf","fonts/Vollkorn/static/Vollkorn-BoldItalic.ttf","fonts/Vollkorn/static/Vollkorn-ExtraBold.ttf","fonts/Vollkorn/static/Vollkorn-ExtraBoldItalic.ttf","fonts/Vollkorn/static/Vollkorn-Italic.ttf","fonts/Vollkorn/static/Vollkorn-Medium.ttf","fonts/Vollkorn/static/Vollkorn-MediumItalic.ttf","fonts/Vollkorn/static/Vollkorn-Regular.ttf","fonts/Vollkorn/static/Vollkorn-SemiBold.ttf","fonts/Vollkorn/static/Vollkorn-SemiBoldItalic.ttf","landing.jpg","robots.txt"]),
	mimeTypes: {".png":"image/png",".ttf":"font/ttf",".txt":"text/plain",".jpg":"image/jpeg"},
	_: {
		client: {start:"_app/immutable/entry/start.CnKoMhFb.js",app:"_app/immutable/entry/app.Gydt6aL3.js",imports:["_app/immutable/entry/start.CnKoMhFb.js","_app/immutable/chunks/BgwmXRPH.js","_app/immutable/chunks/Bdwbqjzo.js","_app/immutable/chunks/mRmwuoWL.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/BUApaBEI.js","_app/immutable/entry/app.Gydt6aL3.js","_app/immutable/chunks/PPVm8Dsz.js","_app/immutable/chunks/mRmwuoWL.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/DsnmJJEf.js","_app/immutable/chunks/Bdwbqjzo.js","_app/immutable/chunks/CoADy4S-.js","_app/immutable/chunks/BTYLiTGZ.js","_app/immutable/chunks/DVENZfLY.js","_app/immutable/chunks/D_n2efGs.js","_app/immutable/chunks/CpZ9HaJX.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/3.js')),
			__memo(() => import('./nodes/4.js')),
			__memo(() => import('./nodes/5.js')),
			__memo(() => import('./nodes/6.js')),
			__memo(() => import('./nodes/7.js')),
			__memo(() => import('./nodes/8.js')),
			__memo(() => import('./nodes/9.js')),
			__memo(() => import('./nodes/10.js')),
			__memo(() => import('./nodes/11.js')),
			__memo(() => import('./nodes/12.js')),
			__memo(() => import('./nodes/13.js')),
			__memo(() => import('./nodes/14.js')),
			__memo(() => import('./nodes/15.js')),
			__memo(() => import('./nodes/16.js')),
			__memo(() => import('./nodes/17.js')),
			__memo(() => import('./nodes/18.js')),
			__memo(() => import('./nodes/19.js')),
			__memo(() => import('./nodes/20.js')),
			__memo(() => import('./nodes/21.js'))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 3 },
				endpoint: __memo(() => import('./entries/endpoints/_server.ts.js'))
			},
			{
				id: "/affinity",
				pattern: /^\/affinity\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 5 },
				endpoint: null
			},
			{
				id: "/a/[item_id]",
				pattern: /^\/a\/([^/]+?)\/?$/,
				params: [{"name":"item_id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 4 },
				endpoint: null
			},
			{
				id: "/c/[folder_id]",
				pattern: /^\/c\/([^/]+?)\/?$/,
				params: [{"name":"folder_id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 6 },
				endpoint: null
			},
			{
				id: "/events",
				pattern: /^\/events\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 7 },
				endpoint: null
			},
			{
				id: "/followers",
				pattern: /^\/followers\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 9 },
				endpoint: null
			},
			{
				id: "/f/[feed_sha256]",
				pattern: /^\/f\/([^/]+?)\/?$/,
				params: [{"name":"feed_sha256","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 8 },
				endpoint: null
			},
			{
				id: "/home",
				pattern: /^\/home\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 10 },
				endpoint: null
			},
			{
				id: "/login",
				pattern: /^\/login\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 11 },
				endpoint: null
			},
			{
				id: "/mota",
				pattern: /^\/mota\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 12 },
				endpoint: null
			},
			{
				id: "/settings",
				pattern: /^\/settings\/?$/,
				params: [],
				page: { layouts: [0,2,], errors: [1,,], leaf: 14 },
				endpoint: null
			},
			{
				id: "/settings/account",
				pattern: /^\/settings\/account\/?$/,
				params: [],
				page: { layouts: [0,2,], errors: [1,,], leaf: 15 },
				endpoint: null
			},
			{
				id: "/settings/affinity",
				pattern: /^\/settings\/affinity\/?$/,
				params: [],
				page: { layouts: [0,2,], errors: [1,,], leaf: 16 },
				endpoint: null
			},
			{
				id: "/settings/appearance",
				pattern: /^\/settings\/appearance\/?$/,
				params: [],
				page: { layouts: [0,2,], errors: [1,,], leaf: 17 },
				endpoint: null
			},
			{
				id: "/settings/data",
				pattern: /^\/settings\/data\/?$/,
				params: [],
				page: { layouts: [0,2,], errors: [1,,], leaf: 18 },
				endpoint: null
			},
			{
				id: "/signup2",
				pattern: /^\/signup2\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 20 },
				endpoint: null
			},
			{
				id: "/signup",
				pattern: /^\/signup\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 19 },
				endpoint: null
			},
			{
				id: "/s/[query]",
				pattern: /^\/s\/([^/]+?)\/?$/,
				params: [{"name":"query","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 13 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();
