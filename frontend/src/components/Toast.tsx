'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useToastStore } from '@/stores/toast-store';

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  return (
    <div className="fixed bottom-8 right-8 z-50 flex flex-col gap-3 pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, y: 24, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.92, transition: { duration: 0.2 } }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            className="pointer-events-auto flex items-center gap-3 px-5 py-3.5 rounded-2xl backdrop-blur-xl border shadow-2xl"
            style={{
              background: 'rgba(10, 10, 10, 0.92)',
              borderColor: toast.type === 'error'
                ? 'rgba(239, 68, 68, 0.3)'
                : 'rgba(244, 187, 146, 0.2)',
              minWidth: '280px',
              maxWidth: '400px',
            }}
          >
            <span className="text-sm text-white/90 flex-1 leading-snug">{toast.message}</span>
            {toast.action && (
              <button
                onClick={toast.action.onClick}
                className="text-xs font-bold uppercase tracking-wider text-amber-400 hover:text-amber-300 transition-colors shrink-0"
              >
                {toast.action.label}
              </button>
            )}
            <button
              onClick={() => removeToast(toast.id)}
              className="text-white/30 hover:text-white/60 transition-colors shrink-0"
            >
              <X size={14} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
