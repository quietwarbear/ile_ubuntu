import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { hasPendingTier } from '../lib/pendingTier';

// This redirect must live inside BrowserRouter. Keeping it separate from App
// lets every sign-in method honor a remembered plan without making the app
// shell itself depend on router context.
export default function PendingTierRedirect() {
  const navigate = useNavigate();

  useEffect(() => {
    if (hasPendingTier()) {
      navigate('/subscriptions', { replace: true });
    }
  }, [navigate]);

  return null;
}
