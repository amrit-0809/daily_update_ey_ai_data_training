
import { Link } from "react-router-dom";

export default function Success({ order }) {
  if (!order) {
    return (
      <main className="container panel">
        <h1>No recent order found</h1>
        <Link to="/">Go to Home</Link>
      </main>
    );
  }

  return (
    <main className="container panel success">
      <div className="checkmark">✓</div>
      <h1>Order Placed Successfully!</h1>
      <p>Thank you for shopping with us.</p>

      <p>
        Order ID: <strong>{order.id}</strong>
      </p>

      <p>Payment: {order.payment}</p>

      <h2>
        Total: ₹{order.total.toLocaleString("en-IN")}
      </h2>

      <Link className="button" to="/">
        Continue Shopping
      </Link>
    </main>
  );
}
