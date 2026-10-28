
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "@/api/client";
import type { DemoUser } from "@/api/client";

export default function LoginPage() {
  const navigate = useNavigate();

  const [users, setUsers] = useState<DemoUser[]>([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [loading, setLoading] = useState(true);
  const [loggingIn, setLoggingIn] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    api.listDemoUsers()
      .then((result) => {
        if (cancelled) return;
        setUsers(result);
        setSelectedUser(result[0]?.id ?? "");
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load demo accounts.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLogin() {
    if (!selectedUser) {
      setError("Please select a demo account.");
      return;
    }

    setLoggingIn(true);
    setError("");

    try {
      const response = await api.loginAs(selectedUser);
      setToken(response.token);
      navigate("/content", { replace: true });
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Login failed.",
      );
    } finally {
      setLoggingIn(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F6F8FC] px-4">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-xl font-bold text-white">
            B
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              BrandGuard
            </h1>
            <p className="text-sm text-slate-500">
              Trusted Content. Stronger Brands.
            </p>
          </div>
        </div>

        <h2 className="text-xl font-semibold text-slate-900">
          Welcome back
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Select a demo account to continue.
        </p>

        {loading ? (
          <p className="mt-6 text-sm text-slate-500">
            Loading demo accounts...
          </p>
        ) : (
          <div className="mt-6 space-y-3">
            {users.map((user) => (
              <label
                key={user.id}
                className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 transition ${
                  selectedUser === user.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="demo-user"
                  value={user.id}
                  checked={selectedUser === user.id}
                  onChange={() => setSelectedUser(user.id)}
                  className="accent-blue-600"
                />
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 font-semibold text-slate-700">
                  {user.initials}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-slate-900">
                    {user.name}
                  </p>
                  <p className="text-sm text-slate-500">
                    {user.title} · {user.team}
                  </p>
                </div>
              </label>
            ))}
          </div>
        )}

        {error && (
          <p
            role="alert"
            className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700"
          >
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={handleLogin}
          disabled={loading || loggingIn || !selectedUser}
          className="mt-6 w-full rounded-xl bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loggingIn ? "Signing in..." : "Sign in to BrandGuard"}
        </button>

        <p className="mt-4 text-center text-xs text-slate-400">
          Development demo environment
        </p>
      </section>
    </main>
  );
}
