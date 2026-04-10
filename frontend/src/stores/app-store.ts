import { create } from 'zustand';

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
  wishlist: string[]; // fragrance IDs
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

export const useAppStore = create<AppState>((set) => ({
  // Seed auth state from storage for refresh-safe route guards.
  authToken: typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null,
  isAuthenticated:
    typeof window !== 'undefined' ? !!localStorage.getItem('auth_token') : false,

  // Default state
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
  adaptiveQuiz: {
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
  },

  // Quiz actions
  setQuizId: (id) => set({ quizId: id }),
  addQuizResponse: (response) =>
    set((state) => ({
      quizResponses: [...state.quizResponses, response],
    })),
  clearQuizResponses: () => set({ quizResponses: [] }),
  setCurrentQuizStep: (step) => set({ currentQuizStep: step }),

  // Adaptive quiz actions
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
      adaptiveQuiz: {
        ...state.adaptiveQuiz,
        phase,
      },
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
  resetAdaptiveQuiz: () =>
    set(() => ({
      adaptiveQuiz: {
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
      },
    })),

  // User actions
  setUserId: (id) => set({ userId: id }),
  updateUserPreferences: (prefs) =>
    set((state) => ({
      userPreferences: { ...state.userPreferences, ...prefs },
    })),

  // Recommendation actions
  setRecommendations: (recs) => set({ recommendations: recs }),

  // Wishlist actions
  addToWishlist: (fragrance_id) =>
    set((state) => ({
      wishlist: [...state.wishlist, fragrance_id],
    })),
  removeFromWishlist: (fragrance_id) =>
    set((state) => ({
      wishlist: state.wishlist.filter((id) => id !== fragrance_id),
    })),

  // Filter actions
  setSelectedFamily: (family) => set({ selectedFamily: family }),

  // Auth actions
  setAuthToken: (token) => {
    localStorage.setItem('auth_token', token);
    if (typeof document !== 'undefined') {
      document.cookie = `auth_token=${token}; path=/; SameSite=Lax`;
    }
    set({ authToken: token, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_id');
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
      adaptiveQuiz: {
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
      },
    });
  },
}));
