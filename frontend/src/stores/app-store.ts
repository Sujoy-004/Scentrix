import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface QuizResponse {
  fragrance_id: string;
  rating: number;
  top_notes?: string[];
  accords?: string[];
  description?: string;
  name?: string;
  brand?: string;
}

export interface UserPreferences {
  gender_neutral: boolean;
  preferred_families?: string[];
  intensity_level?: 'light' | 'medium' | 'strong';
  longevity_preference?: 'short' | 'medium' | 'long';
}

export interface AdaptiveQuizQuestion {
  fragrance_id: string;
  name: string;
  brand: string;
  top_notes: string[];
  accords: string[];
}

export interface AdaptiveQuizRules {
  min_core_questions: number;
  max_total_questions: number;
  medium_extension: number;
  low_extension: number;
  confidence_threshold: number;
}

export interface AdaptiveQuizState {
  sessionId: string | null;
  phase: 'idle' | 'core' | 'extension' | 'final';
  confidenceScore: number | null;
  confidenceBand: 'high' | 'medium' | 'low' | null;
  minCoreQuestions: number;
  maxTotalQuestions: number;
  extensionTarget: number;
  extensionUsed: number;
  questionQueue: AdaptiveQuizQuestion[];
  answeredCount: number;
  answeredCoreCount: number;
  stopReason: string | null;
}

const DEFAULT_ADAPTIVE_QUIZ: AdaptiveQuizState = {
  sessionId: null,
  phase: 'idle',
  confidenceScore: null,
  confidenceBand: null,
  minCoreQuestions: 8,
  maxTotalQuestions: 16,
  extensionTarget: 0,
  extensionUsed: 0,
  questionQueue: [],
  answeredCount: 0,
  answeredCoreCount: 0,
  stopReason: null,
};

interface AppState {
  // Quiz
  quizId: string | null;
  quizResponses: QuizResponse[];
  currentQuizStep: number;
  setQuizId: (id: string) => void;
  addQuizResponse: (response: QuizResponse) => void;
  clearQuizResponses: () => void;
  setCurrentQuizStep: (step: number) => void;

  // Adaptive quiz
  adaptiveQuiz: AdaptiveQuizState;
  initializeAdaptiveQuiz: (payload: {
    sessionId: string;
    seedQuestions: AdaptiveQuizQuestion[];
    rules: AdaptiveQuizRules;
  }) => void;
  appendAdaptiveQuestions: (questions: AdaptiveQuizQuestion[]) => void;
  markAdaptiveAnswer: (isCorePhase: boolean) => void;
  setAdaptivePhase: (phase: AdaptiveQuizState['phase']) => void;
  setAdaptiveConfidence: (payload: {
    confidenceScore: number;
    confidenceBand: AdaptiveQuizState['confidenceBand'];
    extensionTarget: number;
    stopReason: string | null;
  }) => void;
  resetAdaptiveQuiz: () => void;

  // User
  userId: string | null;
  userPreferences: UserPreferences;
  setUserId: (id: string) => void;
  updateUserPreferences: (prefs: Partial<UserPreferences>) => void;

  // Recommendations
  recommendations: any[];
  setRecommendations: (recs: any[]) => void;

  // Wishlist
  wishlist: string[];
  addToWishlist: (fragrance_id: string) => void;
  removeFromWishlist: (fragrance_id: string) => void;

  // Filter
  selectedFamily: string | null;
  setSelectedFamily: (family: string | null) => void;

  // Auth
  isAuthenticated: boolean;
  authToken: string | null;
  setAuthToken: (token: string) => void;
  logout: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // ── State defaults ────────────────────────────────────────────────
      authToken: null,
      isAuthenticated: false,
      quizId: null,
      quizResponses: [],
      currentQuizStep: 0,
      userId: null,
      userPreferences: {
        gender_neutral: true,
        preferred_families: [],
        intensity_level: 'medium',
        longevity_preference: 'long',
      },
      recommendations: [],
      wishlist: [],
      selectedFamily: null,
      adaptiveQuiz: DEFAULT_ADAPTIVE_QUIZ,

      // ── Quiz actions ──────────────────────────────────────────────────
      setQuizId: (id) => set({ quizId: id }),
      addQuizResponse: (response: QuizResponse) =>
        set((state) => {
          if (
            !response.fragrance_id ||
            typeof response.fragrance_id !== "string" ||
            !response.fragrance_id.startsWith("frag_")
          ) {
            console.warn("Invalid fragrance_id:", response.fragrance_id);
            return state;
          }

          const filtered = state.quizResponses.filter(
            (r) => r.fragrance_id !== response.fragrance_id
          );
    
         const updated = [...filtered, response].slice(-20);

         return {
          quizResponses: updated,
        };
      }),
      clearQuizResponses: () => set({ quizResponses: [] }),
      setCurrentQuizStep: (step) => set({ currentQuizStep: step }),

      // ── Adaptive quiz actions ─────────────────────────────────────────
      initializeAdaptiveQuiz: ({ sessionId, seedQuestions, rules }) =>
        set(() => ({
          adaptiveQuiz: {
            sessionId,
            phase: 'core',
            confidenceScore: null,
            confidenceBand: null,
            minCoreQuestions: rules.min_core_questions,
            maxTotalQuestions: rules.max_total_questions,
            extensionTarget: 0,
            extensionUsed: 0,
            questionQueue: seedQuestions,
            answeredCount: 0,
            answeredCoreCount: 0,
            stopReason: null,
          },
        })),
      appendAdaptiveQuestions: (questions) =>
        set((state) => ({
          adaptiveQuiz: {
            ...state.adaptiveQuiz,
            questionQueue: [...state.adaptiveQuiz.questionQueue, ...questions],
            phase: questions.length > 0 ? 'extension' : state.adaptiveQuiz.phase,
          },
        })),
      markAdaptiveAnswer: (isCorePhase) =>
        set((state) => ({
          adaptiveQuiz: {
            ...state.adaptiveQuiz,
            answeredCount: state.adaptiveQuiz.answeredCount + 1,
            answeredCoreCount: isCorePhase
              ? state.adaptiveQuiz.answeredCoreCount + 1
              : state.adaptiveQuiz.answeredCoreCount,
            extensionUsed: isCorePhase
              ? state.adaptiveQuiz.extensionUsed
              : state.adaptiveQuiz.extensionUsed + 1,
          },
        })),
      setAdaptivePhase: (phase) =>
        set((state) => ({
          adaptiveQuiz: { ...state.adaptiveQuiz, phase },
        })),
      setAdaptiveConfidence: ({ confidenceScore, confidenceBand, extensionTarget, stopReason }) =>
        set((state) => ({
          adaptiveQuiz: {
            ...state.adaptiveQuiz,
            confidenceScore,
            confidenceBand,
            extensionTarget,
            stopReason,
          },
        })),
      resetAdaptiveQuiz: () => set({ adaptiveQuiz: DEFAULT_ADAPTIVE_QUIZ }),

      // ── User actions ──────────────────────────────────────────────────
      setUserId: (id) => set({ userId: id }),
      updateUserPreferences: (prefs) =>
        set((state) => ({
          userPreferences: { ...state.userPreferences, ...prefs },
        })),

      // ── Recommendation actions ────────────────────────────────────────
      setRecommendations: (recs) => set({ recommendations: recs }),

      // ── Wishlist actions ──────────────────────────────────────────────
      addToWishlist: (fragrance_id) =>
        set((state) => ({
          wishlist: state.wishlist.includes(fragrance_id)
            ? state.wishlist
            : [...state.wishlist, fragrance_id],
        })),
      removeFromWishlist: (fragrance_id) =>
        set((state) => ({
          wishlist: state.wishlist.filter((id) => id !== fragrance_id),
        })),

      // ── Filter actions ────────────────────────────────────────────────
      setSelectedFamily: (family) => set({ selectedFamily: family }),

      // ── Auth actions ──────────────────────────────────────────────────
      setAuthToken: (token) => {
        // Also set cookie so Next.js middleware can read it server-side
        if (typeof document !== 'undefined') {
          document.cookie = `auth_token=${token}; path=/; SameSite=Lax; max-age=${60 * 60 * 24 * 7}`;
        }
        set({ authToken: token, isAuthenticated: true });
      },
      logout: () => {
        if (typeof document !== 'undefined') {
          document.cookie = 'auth_token=; Max-Age=0; path=/; SameSite=Lax';
        }
        set({
          authToken: null,
          isAuthenticated: false,
          userId: null,
          quizId: null,
          quizResponses: [],
          recommendations: [],
          wishlist: [],
          adaptiveQuiz: DEFAULT_ADAPTIVE_QUIZ,
        });
      },
    }),
    {
      name: 'scentrix-app-state',
      storage: createJSONStorage(() => {
        // SSR-safe: return a no-op storage during server-side rendering
        if (typeof window === 'undefined') {
          return {
            getItem: () => null,
            setItem: () => {},
            removeItem: () => {},
          };
        }
        return localStorage;
      }),
      // Only persist the fields we actually need across refreshes.
      // Never persist `adaptiveQuiz.questionQueue` (too large) or `recommendations`.
      partialize: (state) => ({
        authToken: state.authToken,
        isAuthenticated: state.isAuthenticated,
        userId: state.userId,
        quizResponses: state.quizResponses,
        quizId: state.quizId,
        userPreferences: state.userPreferences,
        wishlist: state.wishlist,
        adaptiveQuiz: state.adaptiveQuiz,
      }),
    }
  )
);
