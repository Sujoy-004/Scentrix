'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Menu, 
  X, 
  Sparkles 
} from 'lucide-react';
import { ScentrixLogo } from './ScentrixLogo';
import './navbar.css';

// Transition Constants for "Quiet Luxury"
const springConfig = { stiffness: 150, damping: 20, mass: 1 };

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  
  const [isClientSide, setIsClientSide] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  const handleSearch = () => {
    const val = searchRef.current?.value;
    router.push(val ? `/?q=${encodeURIComponent(val)}` : '/');
  };

  // Prevent hydration mismatch
  useEffect(() => {
    setIsClientSide(true);
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const menuVariants = {
    closed: {
      opacity: 0,
      scale: 0.95,
      y: -20,
      pointerEvents: 'none' as const,
      transition: { duration: 0.2, ease: 'easeInOut' as const }
    },
    open: {
      opacity: 1,
      scale: 1,
      y: 0,
      pointerEvents: 'auto' as const,
      transition: {
        type: 'spring' as const,
        ...springConfig,
        staggerChildren: 0.05,
        delayChildren: 0.1
      }
    }
  };

  const itemVariants = {
    closed: { opacity: 0, x: -10 },
    open: { opacity: 1, x: 0 }
  };

  if (!isClientSide) return null;

  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
      <div className="navbar-container">
        {/* Logo/Brand with Elite Reveal */}
        <motion.div 
          className="navbar-brand"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          <button
            className="navbar-logo"
            onClick={() => router.push('/')}
          >
            <ScentrixLogo size={36} />
            <span className="logo-text">Scentrix</span>
          </button>
        </motion.div>

        {/* Global Nav Links - Desktop */}
        <div className="navbar-links-desktop">
          <MagneticLink href="/recommendations" isActive={pathname === '/recommendations'} onClick={() => router.push('/recommendations')}>
            Discover
          </MagneticLink>
          <MagneticLink href="/quiz" isActive={pathname === '/quiz'} onClick={() => router.push('/quiz')}>
            Quiz
          </MagneticLink>
          <MagneticLink href="/families" isActive={pathname === '/families'} onClick={() => router.push('/families')}>
            Families
          </MagneticLink>
        </div>


        {/* Hamburger Toggle */}
        <motion.button
          className="navbar-toggle-elite"
          onClick={() => setIsOpen(!isOpen)}
          whileTap={{ scale: 0.9 }}
          aria-label="Toggle menu"
        >
          <AnimatePresence mode="wait">
            {isOpen ? <X size={24} key="x" /> : <Menu size={24} key="menu" />}
          </AnimatePresence>
        </motion.button>
      </div>

      {/* Mobile Menu with Staggered Items */}
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            className="navbar-mobile-menu glass"
            variants={menuVariants}
            initial="closed"
            animate="open"
            exit="closed"
          >
            <div className="mobile-links-container">
              <MobileNavLink icon={<Sparkles size={18} />} label="Discover" onClick={() => { router.push('/recommendations'); setIsOpen(false); }} variants={itemVariants} />
              <MobileNavLink icon={<Sparkles size={18} />} label="Quiz" onClick={() => { router.push('/quiz'); setIsOpen(false); }} variants={itemVariants} />
              <MobileNavLink icon={<Sparkles size={18} />} label="Families" onClick={() => { router.push('/families'); setIsOpen(false); }} variants={itemVariants} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}

function MagneticLink({ children, onClick, isActive }: { children: React.ReactNode, onClick: () => void, href: string, isActive?: boolean }) {
  return (
    <motion.button
      className={`nav-link-magnetic ${isActive ? 'active' : ''}`}
      whileHover={{ y: -2 }}
      whileTap={{ y: 0 }}
      onClick={onClick}
    >
      {children}
      {isActive && (
        <motion.div 
          layoutId="underline" 
          className="nav-link-underline"
          transition={springConfig}
        />
      )}
    </motion.button>
  );
}

function MobileNavLink({ icon, label, onClick, variants }: any) {
  return (
    <motion.button 
      variants={variants}
      className="mobile-nav-link"
      onClick={onClick}
      whileTap={{ x: 10 }}
    >
      {icon} {label}
    </motion.button>
  );
}