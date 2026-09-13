'use client';

import { motion } from 'framer-motion';
import { Sparkles, Brain, Layers } from 'lucide-react';

interface StateIndicatorProps {
  state: number | null;
  stateLabel: string | null;
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
    label: 'Anonymous',
    description: 'Browsing popular scents chosen by our community.',
    strategy: 'Popularity-based ranking',
    nextAction: 'Complete the Discovery Protocol to initialize your neural profile.',
    progressTarget: null,
    icon: 'sparkles',
  },
  1: {
    label: 'Quiz User',
    description: 'Your neural profile is initialized based on your quiz responses.',
    strategy: 'GraphSAGE neural graph — centroid-based KNN search',
    nextAction: 'Rate a fragrance recommendation to begin hybrid personalization.',
    progressTarget: 1,
    icon: 'brain',
  },
  2: {
    label: 'Warm',
    description: 'Feature-based matches refined from your rated scents.',
    strategy: 'Feature-based scoring with accord confidence weights',
    nextAction: 'Keep rating to further refine your profile.',
    progressTarget: null,
    icon: 'layers',
  },
};

const iconMap = {
  sparkles: Sparkles,
  brain: Brain,
  layers: Layers,
};

export default function StateIndicator({ state, stateLabel, ratingCount = 0 }: StateIndicatorProps) {
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
        <div className="state-indicator-badge">
          <IconComponent size={12} />
          <span>STATE {state} &middot; {config.label}</span>
        </div>
        {stateLabel && (
          <span className="state-indicator-code">{stateLabel}</span>
        )}
      </div>

      <p className="state-indicator-desc">{config.description}</p>
      <p className="state-indicator-strategy">{config.strategy}</p>

      <p className="state-indicator-action">
        &rarr; {config.nextAction}
      </p>

      {progress !== null && (
        <div className="state-progress">
          <div className="state-progress-label">
            <span>Progress to next state</span>
            <span>{Math.min(ratingCount, config.progressTarget!)} / {config.progressTarget} ratings</span>
          </div>
          <div className="state-progress-bar">
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
