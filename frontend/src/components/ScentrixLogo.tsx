import React from 'react';
import { motion } from 'framer-motion';

export const ScentrixLogo = ({ size = 32 }: { size?: number }) => {
  return (
    <motion.svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      initial="initial"
      animate="animate"
      className="scentrix-rich-logo"
    >
      <defs>
        <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#C9A86C" />
          <stop offset="50%" stopColor="#F0D090" />
          <stop offset="100%" stopColor="#8B4513" />
        </linearGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Molecular Nexus Geometry */}
      <motion.circle 
        cx="50" cy="50" 
        fill="url(#goldGradient)" 
        filter="url(#glow)" 
        initial={{ r: 14 }} 
        animate={{ scale: [1, 1.05, 1], opacity: [0.8, 1, 0.8] }} 
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }} 
      />
      
      {/* Dynamic Orbital Paths */}
      <motion.circle 
        cx="50" cy="50" r="35" 
        stroke="url(#goldGradient)" 
        strokeWidth="0.5" 
        strokeDasharray="5 15" 
        animate={{ rotate: 360 }} 
        transition={{ duration: 15, repeat: Infinity, ease: "linear" }} 
      />
      <motion.circle 
        cx="50" cy="50" r="45" 
        stroke="url(#goldGradient)" 
        strokeWidth="0.3" 
        opacity="0.4" 
        animate={{ rotate: -360 }} 
        transition={{ duration: 25, repeat: Infinity, ease: "linear" }} 
      />

      {/* Connection Strands (Neural Graph) */}
      <motion.path 
        d="M50 50 L25 25 M50 50 L75 25 M50 50 L75 75 M50 50 L25 75 M50 50 L50 15 M50 50 L50 85" 
        stroke="url(#goldGradient)" 
        strokeWidth="1" 
        strokeLinecap="round" 
        opacity="0.6" 
      />

      {/* Floating Synaptic Nodes */}
      <motion.circle cx="25" cy="25" fill="#C9A86C" initial={{ r: 4 }} animate={{ y: [-3, 3, -3], opacity: [0.6, 1, 0.6] }} transition={{ duration: 3, repeat: Infinity }} />
      <motion.circle cx="75" cy="25" fill="#F0D090" initial={{ r: 3 }} animate={{ y: [3, -3, 3], opacity: [0.6, 1, 0.6] }} transition={{ duration: 3.5, repeat: Infinity }} />
      <motion.circle cx="75" cy="75" fill="#8B4513" initial={{ r: 5 }} animate={{ x: [-2, 2, -2], opacity: [0.6, 1, 0.6] }} transition={{ duration: 4, repeat: Infinity }} />
      <motion.circle cx="25" cy="75" fill="#C9A86C" initial={{ r: 3 }} animate={{ x: [2, -2, 2], opacity: [0.6, 1, 0.6] }} transition={{ duration: 2.8, repeat: Infinity }} />
      <motion.circle cx="50" cy="15" fill="#F0D090" initial={{ r: 2.5 }} animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 2, repeat: Infinity }} />
    </motion.svg>
  );
};
