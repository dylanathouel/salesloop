import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function SignupPage() {
  const { signup } = useAuth();
  const [form, setForm] = useState({
    company_name: "",
    full_name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function update(field: keyof typeof form) {
    return (event: { target: { value: string } }) =>
      setForm((current) => ({ ...current, [field]: event.target.value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await signup(form);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Inscription impossible");
    } finally {
      setPending(false);
    }
  }

  const fields = [
    { key: "company_name" as const, label: "Nom de l'entreprise", type: "text" },
    { key: "full_name" as const, label: "Ton nom complet", type: "text" },
    { key: "email" as const, label: "Email", type: "email" },
    { key: "password" as const, label: "Mot de passe (8 caractères min.)", type: "password" },
  ];

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-zinc-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold">Inscription entreprise</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Crée ton espace SalesLoop — tu seras le compte direction.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {fields.map((field) => (
            <label key={field.key} className="block text-sm">
              <span className="text-zinc-700">{field.label}</span>
              <input
                type={field.type}
                required
                minLength={field.key === "password" ? 8 : 2}
                value={form[field.key]}
                onChange={update(field.key)}
                className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2 focus:border-emerald-500 focus:outline-none"
              />
            </label>
          ))}

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-md bg-zinc-900 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
          >
            {pending ? "Création…" : "Créer l'espace"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-zinc-500">
          Déjà un compte ?{" "}
          <Link to="/login" className="font-medium text-emerald-700 hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
