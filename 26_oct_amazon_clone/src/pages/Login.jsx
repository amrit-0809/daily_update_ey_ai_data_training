
export default function Login({ login }) {
  return (
    <main className="auth-wrap">
      <form className="panel auth-form" onSubmit={login}>
        <h1>Sign In</h1>
        <p>Sign in to continue shopping.</p>

        <label htmlFor="email">Email address</label>
        <input
          id="email"
          name="email"
          type="email"
          placeholder="you@example.com"
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          placeholder="Enter password"
          required
        />

        <button type="submit">Sign In and Continue</button>

        <small>
          Demo only: any valid-format email and non-empty password work.
        </small>
      </form>
    </main>
  );
}
