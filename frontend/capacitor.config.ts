import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
	appId: 'net.bergamonta.app',
	appName: 'Berga',
	webDir: 'build',
	server: {
		androidScheme: 'https',
	},
	plugins: {
		SplashScreen: {
			launchShowDuration: 3000,
			launchAutoHide: false,
			backgroundColor: '#000000',
			showSpinner: false,
			androidScaleType: 'CENTER_CROP',
		},
	},
};

export default config;
