import type { QuizResponse } from '@/stores/app-store';

function intersect<T>(a: T[], b: T[]): T[] {
  const bSet = new Set(b);
  return a.filter((item) => bSet.has(item));
}

function normalizeNotes(notes: string[] | undefined): string[] {
  return (notes || []).map((n) => n.trim().toLowerCase());
}

export function computeReason(
  frag: { id: string; top_notes?: string[]; top_accords?: string[]; reason?: string },
  quizResponses: QuizResponse[],
): string {
  if (!quizResponses || quizResponses.length === 0) {
    return frag.reason || '';
  }

  // Priority 1: Direct match — user rated this exact fragrance
  const directMatch = quizResponses.find((r) => r.fragrance_id === frag.id);
  if (directMatch) {
    return `You rated this ${directMatch.rating}/10`;
  }

  const fragNotes = normalizeNotes(frag.top_notes);

  // Priority 2: Shared notes
  for (const response of quizResponses) {
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
  for (const response of quizResponses) {
    const respAccords = normalizeNotes(response.accords);
    const shared = intersect(fragAccords, respAccords);
    if (shared.length >= 1) {
      return `Similar to your rating of ${response.name}`;
    }
  }

  // Fallback: existing backend reason
  return frag.reason || '';
}
