
import { Link } from "react-router-dom";

export default function Cart({
  cart,
  changeQty,
  total,
  checkout,
}) {
  return (
    <main className="container">
      <h1>Your Shopping Cart</h1>

      {cart.length === 0 ? (
        <section className="panel">
          <p>Your cart is empty.</p>
          <Link className="button" to="/">
            Continue Shopping
          </Link>
        </section>
      ) : (
        <div className="cart-layout">
          <section className="panel">
            {cart.map((item) => (
              <div className="cart-item" key={item.id}>
                <img src={item.image} alt={item.name} />

                <div className="cart-info">
                  <h3>{item.name}</h3>
                  <p>₹{item.price.toLocaleString("en-IN")}</p>

                  <div className="quantity">
                    <button onClick={() => changeQty(item.id, -1)}>
                      −
                    </button>

                    <span>{item.qty}</span>

                    <button onClick={() => changeQty(item.id, 1)}>
                      +
                    </button>
                  </div>

                  <button
                    className="remove"
                    onClick={() => changeQty(item.id, -item.qty)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </section>

          <aside className="panel summary">
            <h2>Order Summary</h2>
            <p>
              Items: {cart.reduce((sum, item) => sum + item.qty, 0)}
            </p>

            <h3>
              Total: ₹{total.toLocaleString("en-IN")}
            </h3>

            <button onClick={checkout}>
              Proceed to Payment
            </button>
          </aside>
        </div>
      )}
    </main>
  );
}
