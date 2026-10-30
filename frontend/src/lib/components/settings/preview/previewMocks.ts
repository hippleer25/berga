/** Static fake content for the settings live-previews. Uses local assets only
 *  (no network), and mirrors the prop contracts of PostCard / EventCard so the
 *  real components can render them verbatim. */

const COVER = '/landing.jpg';
const LOGO = '/berga.png';

export const MOCK_POST = {
	item_id: 'preview-post-1',
	title: 'Designing interfaces that feel hand-crafted',
	description:
		'Great products carry the fingerprints of their makers: deliberate type, patient spacing and honest materials. Here is how to recover the craft in a world of defaults.',
	author: 'A. Sørensen',
	link: 'https://example.com/hand-crafted-interfaces',
	pub_date: new Date().toISOString(),
	feed_title: 'Workshop Journal',
	feed_icon: LOGO,
	feed_sha256: 'preview-feed-0000000000000000000000000000000000000000',
	saved: false,
	image_url: COVER,
	relevance_score: 0.87,
};

export const MOCK_EVENT = {
	summary: 'The quiet return of editorial typography',
	article_count: 5,
	unique_feeds: 3,
	affinity_pct: 72,
	articles: [
		{
			item_id: 'preview-event-1',
			title: 'Serifs are coming back to the web — and here is why it matters',
			url: 'https://example.com/serifs-return',
			source: 'Workshop Journal',
			feed_sha256: 'preview-feed-0000000000000000000000000000000000000000',
			feed_icon: LOGO,
			published_at: new Date(Date.now() - 3600_000).toISOString(),
			image_url: COVER,
			description:
				'After a decade of sans obsession, editorial type is re-shaping English-language reading surfaces.',
		},
		{
			item_id: 'preview-event-2',
			title: 'Reading rhythms: line-height as an identity choice',
			url: 'https://example.com/reading-rhythms',
			source: 'Type Daily',
			feed_sha256: 'preview-feed-1111111111111111111111111111111111111111',
			published_at: new Date(Date.now() - 7200_000).toISOString(),
		},
		{
			item_id: 'preview-event-3',
			title: 'Why quiet relief beats heavy shadows',
			url: 'https://example.com/quiet-relief',
			source: 'Interface Notes',
			feed_sha256: 'preview-feed-2222222222222222222222222222222222222222',
			published_at: new Date(Date.now() - 10_800_000).toISOString(),
		},
	],
};

/** Raw HTML snippet for the fake article body (sanitization is not needed —
 *  it is static, authored markup, rendered via {@html} in a replica only). */
export const MOCK_ARTICLE_BODY = `
<p>Great interfaces are set like trusted publications: the reader notices the
rhythm before the words, and the words land exactly where they should. The
measure, the leading and the hierarchy do the quiet work.</p>
<img src="${COVER}" alt="" />
<p>This sample exists so the typography knobs behave like the real reading
surface — size, weight, letter spacing and line height apply to this block the
same instant they are applied to the app.</p>
`;
