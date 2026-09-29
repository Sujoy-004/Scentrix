'use client';

import { motion } from 'framer-motion';
import { Sparkles, Brain, Layers } from 'lucide-react';

interface StateIndicatorProps {
  state: number | null;
  ratingCount?: number;
}

const STATE_CONFIG: Record<number, {
  label: string;
  description: string;
  strategy: string;
  nextAction: string;
  progressTarget: number | null;
  icon: 'sparkles' | 'brain' | 'layers';
}> = {
  0: {
    label: 'Just browsing',
    description: 'These are the scents our community loves right now.',
    strategy: 'Ordered by overall popularity.',
    nextAction: 'Take the quiz to see picks matched to your own taste.',
    progressTarget: null,
    icon: 'sparkles',
  },
  1: {
    label: 'Profile ready',
    description: 'Your scent profile is built from your quiz answers.',
    strategy: 'Matched to the notes and families you chose.',
    nextAction: 'Rate a fragrance to sharpen your recommendations.',
    progressTarget: 1,
    icon: 'brain',
  },
  2: {
    label: 'Learning your taste',
    description: 'These picks now learn from every scent you rate.',
    strategy: 'Weighted by the notes and families you enjoy most.',
    nextAction: 'Keep rating to keep refining your matches.',
    progressTarget: null,
    icon: 'layers',
  },
};

const iconMap = {
  sparkles: Sparkles,
  brain: Brain,
  layers: Layers,
};

export default function StateIndicator({ state, ratingCount = 0 }: StateIndicatorProps) {
  if (state === null || state === undefined || state < 0 || state > 2) {
    return null;
  }

  const config = STATE_CONFIG[state];
  const IconComponent = iconMap[config.icon];
  const progress = config.progressTarget !== null
    ? Math.min(ratingCount / config.progressTarget, 1)
    : null;

  return (
    <motion.div
      className="state-indicator"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="state-indicator-header">
        <p className="state-indicator-badge">
          <IconComponent size={14} aria-hidden="true" />
          <span>{config.label}</span>
        </p>
      </div>

      <p className="state-indicator-desc">{config.description}</p>
      <p className="state-indicator-strategy">{config.strategy}</p>

      <p className="state-indicator-action">{config.nextAction}</p>

      {progress !== null && (
        <div className="state-progress">
          <div className="state-progress-label">
            <span>Next step</span>
            <span>{Math.min(ratingCount, config.progressTarget!)} of {config.progressTarget} rating</span>
          </div>
          <div
            className="state-progress-bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={config.progressTarget!}
            aria-valuenow={Math.min(ratingCount, config.progressTarget!)}
            aria-label="Ratings toward personalized recommendations"
          >
            <motion.div
              className="state-progress-fill"
              initial={{ width: 0 }}
              animate={{ width: `${progress * 100}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
          </div>
        </div>
      )}
    </motion.div>
  );
}
