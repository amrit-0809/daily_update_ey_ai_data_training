
import { Link } from "react-router-dom";

export default function Navbar({
  query,
  setQuery,
  cartCount,
  user,
}) {
  return (
    <header className="navbar">
      <Link to="/" className="logo">
        amazon<span> clone</span>
      </Link>

      <form
        className="search"
        onSubmit={(e) => e.preventDefault()}
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search products..."
        />
        <button type="submit">Search</button>
      </form>

      <div className="nav-links">
        <Link to="/login">
          {user ? "Your Account" : "Sign In"}
        </Link>
        <Link to="/cart">Cart ({cartCount})</Link>
      </div>
    </header>
  );
}
