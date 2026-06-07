import type { QuizResponse } from '@/stores/app-store';

function intersect<T>(a: T[], b: T[]): T[] {
  const bSet = new Set(b);
  return a.filter((item) => bSet.has(item));
}

function normalizeNotes(notes: string[] | undefined): string[] {
  return (notes || []).map((n) => n.trim().toLowerCase());
}

function describeProfile(quizResponses: QuizResponse[]): string {
  if (!quizResponses.length) return '';
  const avg = quizResponses.reduce((s, r) => s + r.rating, 0) / quizResponses.length;
  const count = quizResponses.length;

  const liked = quizResponses.filter(r => r.rating >= 7);
  const noteCounts = new Map<string, number>();
  for (const r of liked) {
    for (const n of (r.top_notes || [])) {
      noteCounts.set(n, (noteCounts.get(n) || 0) + 1);
    }
  }
  const topNotes = [...noteCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([n]) => n);

  let desc = `Based on your ${count} rating`;
  if (count === 1) {
    const r = quizResponses[0];
    desc = `Because you rated ${r.name}`;
    if (r.rating >= 7) desc += ' highly';
    else if (r.rating <= 4) desc += ' low';
    return desc;
  }
  desc += ` (avg ${avg.toFixed(1)}/10)`;
  if (topNotes.length) {
    desc += ` — you tend to prefer ${topNotes.join(', ')}`;
  }
  return desc;
}

export function computeReason(
  frag: { id: string; top_notes?: string[]; top_accords?: string[]; match_score?: number; reason?: string; name?: string },
  quizResponses: QuizResponse[],
): string | null {
  if (!quizResponses || quizResponses.length === 0) {
    return frag.reason || null;
  }

  // Priority 1: Direct match — user rated this exact fragrance
  const directMatch = quizResponses.find((r) => r.fragrance_id === frag.id);
  if (directMatch) {
    return `You rated this ${directMatch.rating}/10`;
  }

  const fragNotes = normalizeNotes(frag.top_notes);

  // Priority 2: Shared notes with highest-rated fragrances first
  const sorted = [...quizResponses].sort((a, b) => b.rating - a.rating);
  for (const response of sorted) {
    const respNotes = normalizeNotes(response.top_notes);
    const shared = intersect(fragNotes, respNotes);
    if (shared.length >= 1) {
      const notesStr = shared
        .slice(0, 2)
        .map((n) => n.charAt(0).toUpperCase() + n.slice(1))
        .join(' and ');
      return `Shares ${notesStr} with your rating of ${response.name}`;
    }
  }

  const fragAccords = normalizeNotes(frag.top_accords);

  // Priority 3: Shared accords
  for (const response of sorted) {
    const respAccords = normalizeNotes(response.accords);
    const shared = intersect(fragAccords, respAccords);
    if (shared.length >= 1) {
      return `Similar to your rating of ${response.name}`;
    }
  }

  // Priority 4: High match score with profile summary
  if (frag.match_score && frag.match_score >= 50) {
    return `${describeProfile(quizResponses)} (${Math.round(frag.match_score)}% match)`;
  }

  // Priority 5: Try brand match
  const brandMatch = sorted.find(r => {
    const rb = (r.brand || '').toLowerCase();
    const fb = (frag as any).brand?.toLowerCase?.() || '';
    return rb && fb && rb === fb;
  });
  if (brandMatch) {
    return `From ${frag.name?.split(' ')[0] || 'the same brand'} — you rated ${brandMatch.name}`;
  }

  // Fallback
  return frag.reason || null;
}

export function buildLearningSummary(quizResponses: QuizResponse[]): { summary: string; highlights: string[] } {
  if (!quizResponses.length) {
    return { summary: 'No ratings yet.', highlights: [] };
  }

  const count = quizResponses.length;
  const avg = quizResponses.reduce((s, r) => s + r.rating, 0) / count;
  const liked = quizResponses.filter(r => r.rating >= 7);
  const disliked = quizResponses.filter(r => r.rating <= 4);

  const highlights: string[] = [];

  const noteSet = new Set<string>();
  for (const r of liked) {
    for (const n of (r.top_notes || [])) noteSet.add(n);
  }
  const familySet = new Set<string>();
  for (const r of liked) {
    for (const a of (r.accords || [])) familySet.add(a);
  }

  if (liked.length >= 2) {
    highlights.push(`You tend to enjoy scents with notes like ${[...noteSet].slice(0, 3).join(', ')}`);
  }
  if (familySet.size > 0) {
    highlights.push(`Preferred families: ${[...familySet].slice(0, 3).join(', ')}`);
  }
  if (avg >= 7) {
    highlights.push('You generally rate scents generously — you know what you like');
  } else if (avg <= 4) {
    highlights.push('You have discerning taste — not easily impressed');
  }
  highlights.push(`${count} ratings provide a ${count >= 8 ? 'strong' : count >= 5 ? 'moderate' : 'emerging'} signal for recommendations`);

  const summary = `${count} fragrance${count !== 1 ? 's' : ''} rated · avg ${avg.toFixed(1)}/10 · ${liked.length} liked, ${disliked.length} not for you`;
  return { summary, highlights };
}
