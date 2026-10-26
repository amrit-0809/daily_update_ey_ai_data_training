
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="container not-found">
      <h1>404</h1>
      <h2>Page Not Found</h2>
      <p>Sorry, the page you requested does not exist.</p>

      <Link className="button" to="/">
        Go to Home
      </Link>
    </main>
  );
}
