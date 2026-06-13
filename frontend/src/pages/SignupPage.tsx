import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Field, Input } from "../components/ui/Field";

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
    { key: "company_name" as const, label: "Nom de l'entreprise", type: "text", min: 2 },
    { key: "full_name" as const, label: "Ton nom complet", type: "text", min: 2 },
    { key: "email" as const, label: "Email", type: "email", min: undefined },
    { key: "password" as const, label: "Mot de passe (8 caractères min.)", type: "password", min: 8 },
  ];

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm p-8">
        <h1 className="text-xl font-semibold">Inscription entreprise</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Crée ton espace SalesLoop — tu seras le compte direction.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {fields.map((field) => (
            <Field
              key={field.key}
              label={field.label}
              error={field.key === "password" ? error : undefined}
            >
              <Input
                type={field.type}
                required
                minLength={field.min}
                value={form[field.key]}
                onChange={update(field.key)}
              />
            </Field>
          ))}
          <Button type="submit" loading={pending} className="w-full">
            Créer l'espace
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-zinc-500 dark:text-zinc-400">
          Déjà un compte ?{" "}
          <Link to="/login" className="font-medium text-emerald-700 hover:underline dark:text-emerald-400">
            Se connecter
          </Link>
        </p>
      </Card>
    </div>
  );
}
