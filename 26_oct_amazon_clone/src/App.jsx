
import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
  useNavigate,
} from "react-router-dom";

import products from "./products";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Cart from "./pages/Cart";
import Login from "./pages/Login";
import Payment from "./pages/Payment";
import Success from "./pages/Success";
import NotFound from "./pages/NotFound";

import "./index.css";

function readStorage(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function Store() {
  const [cart, setCart] = useState(() =>
    readStorage("shop-cart", [])
  );

  const [user, setUser] = useState(() =>
    readStorage("shop-user", null)
  );

  const [query, setQuery] = useState("");
  const [payment, setPayment] = useState("UPI");

  const [order, setOrder] = useState(() =>
    readStorage("shop-order", null)
  );

  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    localStorage.setItem("shop-cart", JSON.stringify(cart));
  }, [cart]);

  useEffect(() => {
    localStorage.setItem("shop-user", JSON.stringify(user));
  }, [user]);

  useEffect(() => {
    localStorage.setItem("shop-order", JSON.stringify(order));
  }, [order]);

  const cartCount = cart.reduce(
    (sum, item) => sum + item.qty,
    0
  );

  const total = cart.reduce(
    (sum, item) => sum + item.price * item.qty,
    0
  );

  const filteredProducts = products.filter((product) =>
    `${product.name} ${product.category}`
      .toLowerCase()
      .includes(query.trim().toLowerCase())
  );

  function addToCart(product) {
    setCart((current) => {
      const found = current.find(
        (item) => item.id === product.id
      );

      if (found) {
        return current.map((item) =>
          item.id === product.id
            ? { ...item, qty: item.qty + 1 }
            : item
        );
      }

      return [...current, { ...product, qty: 1 }];
    });
  }

  function changeQty(id, amount) {
    setCart((current) =>
      current
        .map((item) =>
          item.id === id
            ? { ...item, qty: item.qty + amount }
            : item
        )
        .filter((item) => item.qty > 0)
    );
  }

  function checkout() {
    if (!cart.length) return;

    navigate(user ? "/payment" : "/login");
  }

  function login(event) {
    event.preventDefault();

    const form = new FormData(event.currentTarget);
    const email = form.get("email");
    const password = form.get("password");

    if (!email || !password) return;

    // Demo authentication only.
    setUser({ email });

    const destination = location.state?.from || "/payment";
    navigate(destination, { replace: true });
  }

  function placeOrder() {
    if (!user) {
      navigate("/login");
      return;
    }

    if (!cart.length) {
      navigate("/");
      return;
    }

    const newOrder = {
      id: "ORD" + Date.now().toString().slice(-8),
      total,
      payment,
      items: cart,
    };

    setOrder(newOrder);
    setCart([]);
    navigate("/success");
  }

  return (
    <>
      <Navbar
        query={query}
        setQuery={setQuery}
        cartCount={cartCount}
        user={user}
      />

      <Routes>
        <Route
          path="/"
          element={
            <Home
              products={filteredProducts}
              addToCart={addToCart}
              query={query}
            />
          }
        />

        <Route
          path="/cart"
          element={
            <Cart
              cart={cart}
              changeQty={changeQty}
              total={total}
              checkout={checkout}
            />
          }
        />

        <Route path="/login" element={<Login login={login} />} />

        <Route
          path="/payment"
          element={
            user ? (
              <Payment
                cart={cart}
                total={total}
                payment={payment}
                setPayment={setPayment}
                placeOrder={placeOrder}
              />
            ) : (
              <Navigate
                to="/login"
                replace
                state={{ from: location.pathname }}
              />
            )
          }
        />

        <Route
          path="/success"
          element={<Success order={order} />}
        />

        <Route path="*" element={<NotFound />} />
      </Routes>

      <footer>Amazon Clone — React Practice Project</footer>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Store />
    </BrowserRouter>
  );
}
