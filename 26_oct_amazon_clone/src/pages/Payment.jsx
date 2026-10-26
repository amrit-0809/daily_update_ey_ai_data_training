
import { Link } from "react-router-dom";

export default function Payment({
  cart,
  total,
  payment,
  setPayment,
  placeOrder,
}) {
  if (cart.length === 0) {
    return (
      <main className="container panel">
        <h1>Your cart is empty</h1>
        <Link to="/">Continue Shopping</Link>
      </main>
    );
  }

  return (
    <main className="container narrow">
      <h1>Choose Payment Method</h1>

      <section className="panel">
        {["UPI", "Credit / Debit Card", "Cash on Delivery"].map(
          (method) => (
            <label className="payment-option" key={method}>
              <input
                type="radio"
                name="payment"
                value={method}
                checked={payment === method}
                onChange={(e) => setPayment(e.target.value)}
              />
              {method}
            </label>
          )
        )}

        <hr />

        <h2>
          Total: ₹{total.toLocaleString("en-IN")}
        </h2>

        <button onClick={placeOrder}>
          Place Order
        </button>

        <p className="muted">
          Demo checkout only. No real payment is processed.
        </p>
      </section>
    </main>
  );
}
