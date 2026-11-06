import React, { useEffect, useRef, useState } from 'react';
import { Button } from '../ui/button';
import { apiGet, apiPost } from '../../lib/api';
import { coursePurchasePlatform, loadCourseProduct, purchaseCourseProduct, restoreCourseProducts } from '../../lib/coursePurchases';

export function NativeCoursePurchase({ courseId, userId, onAccessGranted }) {
  const [product, setProduct] = useState(null);
  const [busy, setBusy] = useState(true);
  const [notice, setNotice] = useState('Loading purchase options…');
  const [pending, setPending] = useState(false);
  const alive = useRef(true);
  const locked = useRef(false);
  useEffect(() => {
    alive.current = true;
    let cancelled = false;
    setProduct(null); setBusy(true); setPending(false);
    apiGet(`/api/courses/${courseId}/purchase-options`).then(async options => {
      const id = options.products?.[coursePurchasePlatform()];
      if (!options.available || !id) throw new Error('In-app purchase for this course is not available yet.');
      const found = await loadCourseProduct(id, userId);
      if (!cancelled) { setProduct(found); setNotice('One-time purchase. No membership required.'); }
    }).catch(e => { if (!cancelled) setNotice(e.message || 'Unable to load purchase options. Please try again.'); })
      .finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; alive.current = false; };
  }, [courseId, userId]);

  const confirm = async () => {
    // Webhook delivery may lag the store sheet. Ask our server, never grant
    // enrollment from client-supplied CustomerInfo or a purchase success flag.
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const result = await apiPost(`/api/courses/${courseId}/confirm-purchase`, {});
      if (!alive.current) return;
      if (result.enrolled) { setPending(false); await onAccessGranted(); return; }
      if (attempt < 2) await new Promise(resolve => setTimeout(resolve, 1000));
    }
    if (alive.current) setNotice('Your purchase is being confirmed. Tap Check access in a moment. You do not need to buy again.');
  };

  const run = async action => {
    if (locked.current) return;
    locked.current = true; setBusy(true);
    try { await action(); }
    catch (e) { if (alive.current) setNotice(e.message || 'We could not confirm access. Please try again.'); }
    finally { locked.current = false; if (alive.current) setBusy(false); }
  };

  const buy = () => run(async () => {
    // Check for an earlier purchase or web enrollment before opening a charge sheet.
    const existing = await apiPost(`/api/courses/${courseId}/confirm-purchase`, {});
    if (!alive.current) return;
    if (existing.enrolled) { await onAccessGranted(); return; }
    const result = await purchaseCourseProduct(product, userId);
    if (!alive.current || result.cancelled) return;
    setPending(true);
    setNotice(result.pending ? 'Your payment is awaiting store approval. Check access after it is approved; you do not need to buy again.' : 'Confirming your course access…');
    if (!result.pending) await confirm();
  });

  return (
    <div className="max-w-xs space-y-2 text-right" data-testid="native-course-purchase" aria-busy={busy}>
      {pending ? (
        <Button disabled={busy} onClick={() => run(confirm)} data-testid="confirm-course-purchase">{busy ? 'Confirming…' : 'Check access'}</Button>
      ) : (
        <Button disabled={busy || !product} onClick={buy} data-testid="buy-course">{busy ? 'Please wait…' : product ? `Buy course · ${product.priceString}` : 'Purchase unavailable'}</Button>
      )}
      <p className="text-xs text-[rgb(var(--text-muted))]" role="status">{notice}</p>
      <button type="button" disabled={busy} className="text-xs underline disabled:opacity-50" onClick={() => run(async () => {
        await restoreCourseProducts(userId);
        if (!alive.current) return;
        const result = await apiPost(`/api/courses/${courseId}/confirm-purchase`, {});
        if (result.enrolled) await onAccessGranted();
        else setNotice('No purchase for this course was found. Check that you are using the same store and Ile Ubuntu accounts.');
      })} data-testid="restore-course-purchases">Restore purchases</button>
    </div>
  );
}
