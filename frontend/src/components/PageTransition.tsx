'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { usePathname } from 'next/navigation';
import React, { ReactNode } from 'react';

interface PageTransitionProps extends HTMLMotionProps<'div'> {
  children: ReactNode;
}

const variants = {
  hidden: { opacity: 0, y: 10 },
  enter: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
};

export default function PageTransition({ children, ...props }: PageTransitionProps) {
  const pathname = usePathname();

  return (
    <motion.div
      key={pathname}
      initial="hidden"
      animate="enter"
      exit="exit"
      variants={variants}
      transition={{ 
        type: 'spring', 
        stiffness: 100, 
        damping: 20,
        mass: 1,
        duration: 0.6 
      }}
      className="w-full h-full flex flex-col"
      {...props}
    >
      {children}
    </motion.div>
  );
}
