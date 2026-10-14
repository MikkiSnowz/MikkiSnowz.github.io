import { useState } from 'react';
import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';

const publishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;
const stripePromise = publishableKey ? loadStripe(publishableKey) : null;

function PaymentForm({ returnUrl }) {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState('');
  const [paying, setPaying] = useState(false);

  async function pay(e) {
    e.preventDefault();
    if (!stripe || !elements) return;
    setPaying(true);
    setError('');
    // On success Stripe redirects to returnUrl (the order status page).
    const { error: stripeError } = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: returnUrl },
    });
    setError(stripeError?.message || 'Payment failed');
    setPaying(false);
  }

  return (
    <form onSubmit={pay}>
      <PaymentElement />
      {error && <p className="error">{error}</p>}
      <button className="button full" disabled={!stripe || paying}>
        {paying ? 'Processing…' : 'Pay'}
      </button>
    </form>
  );
}

export default function StripePayment({ clientSecret, returnUrl }) {
  if (!stripePromise) {
    return <p className="error">Card payments are not set up (VITE_STRIPE_PUBLISHABLE_KEY is missing).</p>;
  }
  return (
    <Elements stripe={stripePromise} options={{ clientSecret }}>
      <PaymentForm returnUrl={returnUrl} />
    </Elements>
  );
}
