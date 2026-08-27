export type TagRef = {
	tag_id: number;
	name: string;
	color?: string;
	source: string;
};

type FeedItem = {
	item_id: string;
	tags?: TagRef[];
	[k: string]: any;
};

/**
 * Updates a single feed item's `tags` array in place-style (returns a new array)
 * after an optimistic assign/unassign. Used by feed-list pages when PostCard
 * emits `ontagchange`, so that the parent `feed` array stays in sync with the
 * PostCard's local state and survives bulk-assign rebuilds.
 */
export function syncFeedItemTags(
	feed: FeedItem[],
	itemId: string,
	tagId: number,
	action: 'assign' | 'unassign',
	newTag?: TagRef
): FeedItem[] {
	return feed.map((it) => {
		if (it.item_id !== itemId) return it;
		const existing = it.tags ?? [];
		if (action === 'assign') {
			if (existing.some((t) => t.tag_id === tagId)) return it;
			return {
				...it,
				tags: [
					...existing,
					newTag ?? { tag_id: tagId, name: '', color: undefined, source: 'manual' }
				]
			};
		}
		return { ...it, tags: existing.filter((t) => t.tag_id !== tagId) };
	});
}