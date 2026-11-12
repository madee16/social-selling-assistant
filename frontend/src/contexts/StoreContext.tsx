import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { Merchant, Store } from '../types';
import { getMerchant, listStores } from '../api/merchants';
import { useAuth } from './AuthContext';

interface StoreContextType {
  merchant: Merchant | null;
  stores: Store[];
  loading: boolean;
  activeStoreId: string | null;
  activeStore: Store | null;
  merchantMissing: boolean;
  setActiveStoreId: (id: string) => void;
  reload: () => Promise<void>;
}

const StoreContext = createContext<StoreContextType | null>(null);

const STORAGE_KEY = 'active_store_id';

export function StoreProvider({ children }: { children: ReactNode }) {
  const { user, token } = useAuth();
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);
  const [merchantMissing, setMerchantMissing] = useState(false);
  const [activeStoreId, setActiveStoreId] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!user || !token) {
      setMerchant(null);
      setStores([]);
      setLoading(false);
      setMerchantMissing(false);
      return;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        let m: Merchant | null = null;
        try {
          m = await getMerchant();
          setMerchantMissing(false);
        } catch {
          m = null;
          setMerchantMissing(true);
        }
        if (cancelled) return;
        setMerchant(m);
        if (m) {
          const res = await listStores({ page_size: 100 });
          if (cancelled) return;
          setStores(res.items);
        } else {
          setStores([]);
        }
      } catch (err) {
        console.error('Failed to load store context', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [user?.id, token, reloadKey]);

  const setActive = useCallback((id: string) => {
    localStorage.setItem(STORAGE_KEY, id);
    setActiveStoreId(id);
  }, []);

  const reload = useCallback(async () => {
    setReloadKey((k) => k + 1);
  }, []);

  const activeStore = stores.find((s) => s.id === activeStoreId) ?? null;

  return (
    <StoreContext.Provider
      value={{ merchant, stores, loading, activeStoreId, activeStore, merchantMissing, setActiveStoreId: setActive, reload }}
    >
      {children}
    </StoreContext.Provider>
  );
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used within StoreProvider');
  return ctx;
}