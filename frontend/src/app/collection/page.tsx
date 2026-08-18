'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useWishlist, useRemoveFromWishlist, useUpdateSavedNotes } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { FlaskConical, X, Save, Trash2, ArrowLeft, ExternalLink } from 'lucide-react';
import './collection.css';

export default function CollectionPage() {
  const router = useRouter();
  const { isAuthenticated } = useAppStore();
  const { data: collection = [], isLoading, error } = useWishlist();
  const removeMutation = useRemoveFromWishlist();
  const updateNotesMutation = useUpdateSavedNotes();

  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [editingNotes, setEditingNotes] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) return null;

  const handleOpenDetail = (item: any) => {
    setSelectedItem(item);
    setEditingNotes(item.notes || '');
  };

  const handleSaveNotes = async () => {
    if (!selectedItem) return;
    await updateNotesMutation.mutateAsync({
      id: selectedItem.id,
      notes: editingNotes
    });
    setSelectedItem({ ...selectedItem, notes: editingNotes });
  };

  const handleRemove = async (id: number) => {
    if (confirm('Are you sure you want to remove this fragrance from your collection?')) {
      await removeMutation.mutateAsync(id);
      setSelectedItem(null);
    }
  };

  // Group collection into "shelves" of 4
  const shelfRows = [];
  for (let i = 0; i < collection.length; i += 4) {
    shelfRows.push(collection.slice(i, i + 4));
  }

  return (
    <div className="collection-page">
      <div className="collection-container">
        <header className="collection-header">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            Virtual Scent Shelf
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            A curated archive of your olfactive journey.
          </motion.p>
        </header>

        {isLoading ? (
          <div className="loading-state">
            <FlaskConical className="animate-spin" />
            <p>Hydrating your shelf...</p>
          </div>
        ) : collection.length === 0 ? (
          <div className="empty-state">
            <p>Your shelf is currently empty.</p>
            <button className="btn-primary" onClick={() => router.push('/fragrances')}>
              Discover Fragrances
            </button>
          </div>
        ) : (
          <div className="shelf-system">
            {shelfRows.map((row, rowIndex) => (
              <div key={rowIndex} className="shelf-row">
                <div className="shelf-grid">
                  {row.map((item: any, itemIndex: number) => {
                    const fragrance = item.fragrance ?? { name: 'Unknown', brand: 'Archive' };
                    return (
                      <motion.div
                        key={item.id}
                        className="scent-bottle"
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ 
                          duration: 0.5, 
                          delay: (rowIndex * 4 + itemIndex) * 0.1 
                        }}
                        onClick={() => handleOpenDetail(item)}
                      >
                        <div className="bottle-vessel">
                          <div className="bottle-liquid" />
                          <div className="bottle-label">
                            <p className="brand">{fragrance.brand}</p>
                            <p className="name">{fragrance.name}</p>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
                <div className="shelf-line" />
              </div>
            ))}
          </div>
        )}

        <div className="navigation-footer">
          <button className="back-link" onClick={() => router.push('/')}>
            <ArrowLeft size={16} /> Dashboard
          </button>
        </div>
      </div>

      <AnimatePresence>
        {selectedItem && (
          <motion.div
            className="scent-portal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={(e) => e.target === e.currentTarget && setSelectedItem(null)}
          >
            <motion.div
              className="scent-portal-content"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            >
              <div className="portal-visual">
                <div className="hero-bottle">
                   <FlaskConical size={120} strokeWidth={1} color="#d4af37" />
                </div>
              </div>
              <div className="portal-details">
                <div className="portal-header">
                   <p className="brand">{(selectedItem.fragrance?.brand || 'Scentrix Archive').toUpperCase()}</p>
                   <h2>{selectedItem.fragrance?.name || 'Neural Artifact'}</h2>
                </div>

                <div className="portal-meta">
                  <span className="meta-pill">{selectedItem.fragrance?.family || 'Universal'}</span>
                  <span className="meta-pill">Added {new Date(selectedItem.created_at).toLocaleDateString()}</span>
                </div>

                <div className="portal-notes-section">
                  <h4>Personal Olfactive Notes</h4>
                  <textarea
                    className="notes-textarea"
                    placeholder="Describe the memory or sensation this scent evokes..."
                    value={editingNotes}
                    onChange={(e) => setEditingNotes(e.target.value)}
                  />
                </div>

                <div className="portal-actions">
                  <button 
                    className="btn-primary flex items-center gap-2"
                    onClick={handleSaveNotes}
                    disabled={updateNotesMutation.isPending}
                  >
                    <Save size={18} /> {updateNotesMutation.isPending ? 'Syncing...' : 'Save Notes'}
                  </button>
                  <button 
                    className="btn-danger flex items-center gap-2"
                    onClick={() => handleRemove(selectedItem.id)}
                    disabled={removeMutation.isPending}
                  >
                    <Trash2 size={18} /> Remove
                  </button>
                  <button
                    className="meta-pill flex items-center gap-2"
                    onClick={() => router.push(`/fragrances/${selectedItem.fragrance_neo4j_id}`)}
                  >
                   Full Analysis <ExternalLink size={14} />
                  </button>
                </div>

                <button 
                  className="absolute top-6 right-6 p-2 text-gray-500 hover:text-white"
                  onClick={() => setSelectedItem(null)}
                >
                  <X size={24} />
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
