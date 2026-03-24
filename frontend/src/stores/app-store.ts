import { create } from 'zustand';

export interface QuizResponse {
  fragrance_id: string;
  rating: number;
  notes?: string;
}

export interface UserPreferences {
  gender_neutral: boolean;
  preferred_families?: string[];
  intensity_level?: 'light' | 'medium' | 'strong';
  longevity_preference?: 'short' | 'medium' | 'long';
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
  isAuthenticated: false,
  authToken: typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null,

  // Quiz actions
  setQuizId: (id) => set({ quizId: id }),
  addQuizResponse: (response) =>
    set((state) => ({
      quizResponses: [...state.quizResponses, response],
    })),
  clearQuizResponses: () => set({ quizResponses: [] }),
  setCurrentQuizStep: (step) => set({ currentQuizStep: step }),

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
    set({ authToken: token, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('auth_token');
    set({
      authToken: null,
      isAuthenticated: false,
      userId: null,
      quizId: null,
      quizResponses: [],
      recommendations: [],
      wishlist: [],
    });
  },
}));
