import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { sendMessage, listConversations, getConversationDetail, closeConversation, type ProductCardData } from '../api/chat';
import { listProducts } from '../api/products';
import { createOrder } from '../api/orders';
import { useToast } from '../contexts/ToastContext';
import type { Conversation, Message } from '../types';
import type { Product } from '../types';
import { Button, Badge, Input, Modal } from '../components/ui';

function ProductCard({ product }: { product: ProductCardData }) {
  return (
    <a href={product.image_url || '#'} target={product.image_url ? '_blank' : undefined} rel="noopener noreferrer"
      className="shrink-0 w-40 rounded-xl border border-slate-200/90 overflow-hidden bg-white hover:shadow-md hover:border-blue-300 transition-all dark:bg-slate-800 dark:border-slate-700 shadow-2xs">
      <div className="h-24 bg-slate-100 flex items-center justify-center overflow-hidden dark:bg-slate-750">
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
        ) : (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
        )}
      </div>
      <div className="p-2.5">
        <p className="text-xs font-semibold text-slate-900 truncate dark:text-slate-100">{product.name}</p>
        <p className="text-xs font-bold text-blue-600 dark:text-blue-400 mt-0.5">{product.price.toFixed(2)} TND</p>
      </div>
    </a>
  );
}

function FeaturedProducts({ products, loadingProducts: lp }: { products: Product[]; loadingProducts: boolean }) {
  const featured = products.slice(0, 6);
  if (lp || featured.length === 0) return null;
  return (
    <div className="py-4">
      <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider dark:text-gray-400">Produits populaires</p>
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
        {featured.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
    </div>
  );
}

const LANGUAGES = [
  { value: 'fr', label: 'Français' },
  { value: 'en', label: 'English' },
  { value: 'ar', label: 'العربية' },
];

const CHAT_STORAGE_KEY = 'ss_active_chat_id';

export default function Chat() {
  const { t } = useTranslation();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [customerAddress, setCustomerAddress] = useState('');
  const [language, setLanguage] = useState('fr');
  const [showNewForm, setShowNewForm] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [orderItems, setOrderItems] = useState<{ product_id: string; quantity: number }[]>([]);
  const [creatingOrder, setCreatingOrder] = useState(false);
  const msgsEndRef = useRef<HTMLDivElement>(null);
  const { showToast } = useToast();

  const fetchConversations = async () => {
    setLoadingList(true);
    try {
      const data = await listConversations({ page_size: 50 });
      setConversations(data.items);
      const stored = localStorage.getItem(CHAT_STORAGE_KEY);
      if (stored && data.items.some((c) => c.id === stored)) setSelectedId(stored);
    } finally { setLoadingList(false); }
  };

  const fetchProducts = async () => {
    setLoadingProducts(true);
    try { const data = await listProducts({ active_only: true, page_size: 100 }); setProducts(data.items); } finally { setLoadingProducts(false); }
  };

  useEffect(() => { fetchConversations(); fetchProducts(); }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoadingMsgs(true);
    getConversationDetail(selectedId)
      .then((data) => {
        setMessages(data.messages);
        setCustomerName(data.conversation.customer_name || '');
        setCustomerPhone(data.conversation.customer_phone || '');
        setCustomerAddress(data.conversation.customer_address || '');
        setLanguage(data.conversation.language || 'fr');
      })
      .finally(() => setLoadingMsgs(false));
  }, [selectedId]);

  useEffect(() => { msgsEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    const userMsg: Message = {
      id: 'temp-' + Date.now(), conversation_id: selectedId || '', role: 'user', content: text, language: language, extra_data: null, created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    try {
      const res = await sendMessage({ conversation_id: selectedId || undefined, customer_name: customerName || undefined, customer_phone: customerPhone || undefined, customer_address: customerAddress || undefined, language, message: text });
      setSelectedId(res.conversation_id);
      localStorage.setItem(CHAT_STORAGE_KEY, res.conversation_id);
      if (res.order) {
        showToast('success', `Order created: ${res.order.total.toFixed(2)} TND (${res.order.items} items)`);
        fetchConversations();
      }
      const aiExtra: Record<string, unknown> = {};
      if (res.order) { aiExtra.order_id = res.order.id; aiExtra.total = res.order.total; }
      if (res.suggested_products?.length) { aiExtra.suggested_products = res.suggested_products; }
      const aiMsg: Message = {
        id: 'temp-ai-' + Date.now(), conversation_id: res.conversation_id, role: 'assistant', content: res.reply, language: res.language, extra_data: aiExtra, created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);
      fetchConversations();
    } finally { setSending(false); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleClose = async () => {
    if (!selectedId) return;
    await closeConversation(selectedId);
    localStorage.removeItem(CHAT_STORAGE_KEY);
    setSelectedId(null); setMessages([]); fetchConversations();
  };

  const handleCreateOrder = async () => {
    if (orderItems.length === 0 || !selectedId || !customerName) return;
    setCreatingOrder(true);
    try {
      await createOrder({
        conversation_id: selectedId, customer_name: customerName, customer_phone: customerPhone || undefined, customer_address: customerAddress || undefined,
        items: orderItems.map(oi => { const product = products.find(p => p.id === oi.product_id); return { product_id: oi.product_id, quantity: oi.quantity, unit_price: product?.price || 0 }; }),
      });
      setShowOrderModal(false); setOrderItems([]); showToast('success', 'Order created successfully');
      fetchConversations();
    } catch (err) { console.error('Failed to create order:', err); showToast('error', 'Failed to create order'); } finally { setCreatingOrder(false); }
  };

  const handleNew = () => {
    localStorage.removeItem(CHAT_STORAGE_KEY);
    setSelectedId(null); setMessages([]); setCustomerName(''); setCustomerPhone(''); setCustomerAddress(''); setLanguage('fr'); setShowNewForm(true);
  };

  const selectConv = (id: string) => { setSelectedId(id); setShowNewForm(false); localStorage.setItem(CHAT_STORAGE_KEY, id); };

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-4">
      <div className="w-72 shrink-0 bg-white rounded-xl border border-gray-200 flex flex-col dark:bg-gray-900 dark:border-gray-700">
        <div className="p-3 border-b border-slate-100 flex items-center justify-between dark:border-slate-800">
          <h2 className="font-bold text-sm text-slate-900 dark:text-slate-100">{t('chat.conversations')}</h2>
          <Button size="sm" onClick={handleNew}>{t('chat.new')}</Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loadingList ? (
            <div className="p-3 space-y-2">{[1,2,3].map(i => <div key={i} className="h-14 bg-slate-100 animate-pulse rounded-lg dark:bg-slate-800" />)}</div>
          ) : conversations.length === 0 ? (
            <p className="text-slate-400 text-sm p-4 text-center dark:text-slate-500">{t('chat.no_conversations')}</p>
          ) : (
            conversations.map((c) => (
              <button key={c.id} onClick={() => selectConv(c.id)}
                className={`w-full text-left p-3 border-b border-slate-100/70 hover:bg-slate-50/70 transition-colors dark:border-slate-800 dark:hover:bg-slate-800/50 cursor-pointer ${selectedId === c.id ? 'bg-blue-50/70 border-l-4 border-l-blue-600 dark:bg-blue-500/15' : ''}`}>
                <div className="text-sm font-semibold text-slate-900 truncate dark:text-slate-100">{c.customer_name || 'Anonymous'}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <Badge variant={c.status === 'active' ? 'success' : 'info'} size="sm">{c.status}</Badge>
                  <span className="text-xs text-slate-400 dark:text-slate-500 font-medium">{c.language?.toUpperCase() || 'FR'}</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1 dark:text-slate-500">{new Date(c.updated_at).toLocaleString()}</div>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 bg-white rounded-xl border border-slate-200/90 flex flex-col dark:bg-slate-900 dark:border-slate-800 shadow-xs">
        {showNewForm && !selectedId ? (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="w-full max-w-md space-y-4">
              <h3 className="text-lg font-bold text-slate-900 text-center dark:text-slate-100">{t('chat.new_conversation')}</h3>
              <Input label={t('chat.customer_name')} value={customerName} onChange={(e) => setCustomerName(e.target.value)} placeholder={t('chat.optional')} />
              <Input label={t('orders.phone')} value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value)} placeholder={t('chat.optional')} />
              <Input label={t('chat.address')} value={customerAddress} onChange={(e) => setCustomerAddress(e.target.value)} placeholder={t('chat.optional')} />
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5 dark:text-slate-300">{t('chat.language')}</label>
                <select value={language} onChange={(e) => setLanguage(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 dark:bg-slate-800 dark:text-slate-100">
                  {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5 dark:text-slate-300">{t('chat.first_message')}</label>
                <textarea value={input} onChange={(e) => setInput(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600" rows={3} placeholder={t('chat.type_message')} />
              </div>
              <Button onClick={handleSend} disabled={!input.trim() || sending} className="w-full">
                {sending ? `${t('common.loading')}...` : t('chat.start_conversation')}
              </Button>
            </div>
          </div>
        ) : selectedId ? (
          <>
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm dark:bg-blue-500/20 dark:text-blue-300 ring-2 ring-blue-500/20">
                  {(customerName || 'A')[0].toUpperCase()}
                </div>
                <div>
                  <span className="font-bold text-sm text-slate-900 dark:text-slate-100">{customerName || 'Anonymous'}</span>
                  {customerPhone && <span className="text-xs text-slate-400 ml-2 dark:text-slate-500">· {customerPhone}</span>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="success" onClick={() => setShowOrderModal(true)}>{t('chat.create_order')}</Button>
                <select value={language} onChange={(e) => setLanguage(e.target.value)}
                  className="rounded-lg border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                  {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
                </select>
                <button onClick={handleClose} className="text-xs text-rose-600 hover:text-rose-800 font-semibold cursor-pointer">{t('chat.close')}</button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {loadingMsgs ? (
                <div className="space-y-3">{[1,2,3].map(i => (
                  <div key={i} className="flex justify-start">
                    <div className="h-12 w-48 rounded-xl skeleton" />
                  </div>
                ))}</div>
              ) : messages.length === 0 && !loadingMsgs ? (
                <FeaturedProducts products={products} loadingProducts={loadingProducts} />
              ) : (
                messages.map((m) => (
                  <div key={m.id} className="space-y-2">
                    <div className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${m.role === 'user' ? 'bg-blue-600 text-white rounded-br-xs shadow-xs' : 'bg-slate-100 text-slate-900 rounded-bl-xs border border-slate-200/50 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-700/60 shadow-2xs'}`}>
                        {!!m.extra_data?.order_id && (
                          <div className="mb-2 inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 text-xs font-semibold px-2.5 py-1 rounded-full dark:bg-emerald-500/15 dark:text-emerald-400">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
                            Order created · {(m.extra_data as { total?: number }).total?.toFixed(2)} TND
                          </div>
                        )}
                        <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
                        <div className={`text-[10px] mt-1 font-medium ${m.role === 'user' ? 'text-blue-100/80' : 'text-slate-400 dark:text-slate-500'}`}>
                          {m.language?.toUpperCase() || ''} · {new Date(m.created_at).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                    {m.role === 'assistant' && !!((m.extra_data as Record<string, unknown>)?.suggested_products) && (
                      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
                        {((m.extra_data as Record<string, unknown>).suggested_products as ProductCardData[]).map((p) => (
                          <ProductCard key={p.id} product={p} />
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
              {sending && messages[messages.length - 1]?.role === 'user' && (
                <div className="flex justify-start">
                  <div className="max-w-[75%] rounded-2xl px-4 py-3 bg-slate-100 text-slate-900 rounded-bl-xs border border-slate-200/50 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-700/60 shadow-2xs">
                    <span className="loading-dots text-slate-400 dark:text-slate-500">
                      <span /><span /><span />
                    </span>
                  </div>
                </div>
              )}
              <div ref={msgsEndRef} />
            </div>

            <div className="p-4 border-t border-slate-100 dark:border-slate-800">
              <div className="flex gap-2 items-end">
                <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
                  className="flex-1 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 transition-all"
                  rows={2} placeholder={t('chat.type_message')} disabled={sending} />
                <Button onClick={handleSend} disabled={!input.trim() || sending} className="px-4 self-end">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-400 dark:text-slate-500">
            <div className="text-center">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto mb-3 text-slate-300 dark:text-slate-600">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
              <p className="mb-2 font-medium">{t('chat.select_or_start')}</p>
              <Button onClick={handleNew}>{t('chat.new')}</Button>
            </div>
          </div>
        )}
      </div>

      <Modal open={showOrderModal} onClose={() => setShowOrderModal(false)} title={t('chat.create_order')}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><p className="text-gray-500 dark:text-gray-400">{t('orders.customer')}</p><p className="font-medium">{customerName || 'Anonymous'}</p></div>
            <div><p className="text-gray-500 dark:text-gray-400">{t('orders.phone')}</p><p>{customerPhone || '-'}</p></div>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2 dark:text-gray-200">{t('orders.items')}</h4>
            {loadingProducts ? (
              <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-12 bg-gray-100 animate-pulse rounded-lg dark:bg-gray-700" />)}</div>
            ) : products.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500">{t('chat.no_products')}</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {products.map((p) => {
                  const existing = orderItems.find(oi => oi.product_id === p.id);
                  const qty = existing?.quantity || 0;
                  return (
                    <div key={p.id} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800">
                      <div className="flex-1">
                        <p className="font-medium text-sm text-gray-900 dark:text-gray-100">{p.name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{p.price.toFixed(2)} TND</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => setOrderItems(prev => prev.filter(oi => oi.product_id !== p.id))}
                          disabled={qty === 0} className="w-7 h-7 rounded-lg border border-gray-300 bg-white text-gray-700 flex items-center justify-center text-sm disabled:opacity-30 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700">−</button>
                        <span className="w-6 text-center text-sm font-medium">{qty}</span>
                        <button onClick={() => setOrderItems(prev => [...prev.filter(oi => oi.product_id !== p.id), { product_id: p.id, quantity: qty + 1 }])}
                          disabled={qty >= p.stock_quantity} className="w-7 h-7 rounded-lg border border-gray-300 bg-white text-gray-700 flex items-center justify-center text-sm disabled:opacity-30 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700">+</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          {orderItems.length > 0 && (
            <div className="bg-gray-50 p-4 rounded-xl dark:bg-gray-800">
              <h4 className="text-sm font-semibold text-gray-700 mb-2 dark:text-gray-200">{t('orders.orders')} {t('orders.subtotal')}</h4>
              <div className="space-y-1.5">
                {orderItems.map(oi => {
                  const prod = products.find(p => p.id === oi.product_id);
                  return (
                    <div key={oi.product_id} className="flex justify-between text-sm text-gray-700 dark:text-gray-200">
                      <span>{prod?.name} × {oi.quantity}</span>
                      <span>{(prod ? prod.price * oi.quantity : 0).toFixed(2)} TND</span>
                    </div>
                  );
                })}
                <div className="border-t border-gray-200 pt-1.5 font-semibold flex justify-between text-sm text-gray-900 dark:border-gray-700 dark:text-gray-100">
                  <span>{t('orders.total')}</span>
                  <span>{orderItems.reduce((sum, oi) => { const prod = products.find(p => p.id === oi.product_id); return sum + (prod ? prod.price * oi.quantity : 0); }, 0).toFixed(2)} TND</span>
                </div>
              </div>
            </div>
          )}
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={() => { setShowOrderModal(false); setOrderItems([]); }}>{t('common.cancel')}</Button>
            <Button variant="success" onClick={handleCreateOrder} disabled={orderItems.length === 0 || creatingOrder || !customerName.trim()} loading={creatingOrder}>
              {t('chat.create_order')}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
