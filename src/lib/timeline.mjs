/**
 * The tracking log as rows for the homepage timeline: newest first, grouped by
 * month, each row headed by its topic and pointing at the commitment's anchor
 * on the topic page.
 */
import { updatesLog } from './plan.mjs';

/**
 * @param {{ log?: { date: string, item: string, status: string, text: string }[] }} tracking
 * @param {{ topics: { id: string, slug: string, name: string }[] }} plan
 */
export function timelineEntries(tracking, plan) {
  const topics = new Map(plan.topics.map((topic) => [topic.id, topic]));
  const seen = new Map();
  return updatesLog(tracking).map((entry) => {
    const topic = topics.get(entry.item.split('.')[0]);
    // Two log lines can share a day and an item; the id must still be unique.
    const base = `${entry.date}-${entry.item}`;
    const n = (seen.get(base) ?? 0) + 1;
    seen.set(base, n);
    return {
      id: n === 1 ? base : `${base}-${n}`,
      date: entry.date,
      month: entry.date.slice(0, 7),
      status: entry.status,
      item: entry.item,
      text: entry.text,
      topicName: topic?.name ?? null,
      href: topic ? `/temas/${topic.slug}/#${entry.item}` : null,
    };
  });
}
