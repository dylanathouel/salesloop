import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { useChangePassword } from "../api/hooks";
import type { UserRole } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Field, Input } from "../components/ui/Field";
import { useToast } from "../components/ui/Toast";

const ROLE_LABELS: Record<UserRole, string> = {
  commercial: "Commercial",
  manager: "Manager",
  direction: "Direction",
};

export function ProfilePage() {
  const { user } = useAuth();
  const changePassword = useChangePassword();
  const toast = useToast();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!user) return null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (newPassword !== confirm) {
      setError("Les deux mots de passe ne correspondent pas");
      return;
    }
    changePassword.mutate(
      { old_password: oldPassword, new_password: newPassword },
      {
        onSuccess: () => {
          toast.success("Mot de passe mis à jour");
          setOldPassword("");
          setNewPassword("");
          setConfirm("");
        },
        onError: (err) => {
          const message = err instanceof ApiError ? err.message : "Modification impossible";
          setError(message);
          toast.error(message);
        },
      },
    );
  }

  const infos: { label: string; value: string }[] = [
    { label: "Nom", value: user.full_name },
    { label: "Email", value: user.email },
    { label: "Rôle", value: ROLE_LABELS[user.role] },
  ];

  return (
    <div className="mx-auto max-w-2xl space-y-6 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Mon profil</h1>

      <Card className="divide-y divide-zinc-100 dark:divide-zinc-800">
        {infos.map((info) => (
          <div key={info.label} className="flex justify-between px-5 py-3 text-sm">
            <span className="text-zinc-500 dark:text-zinc-400">{info.label}</span>
            <span className="font-medium">{info.value}</span>
          </div>
        ))}
      </Card>

      <Card className="p-5">
        <h2 className="text-sm font-semibold">Changer le mot de passe</h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <Field label="Mot de passe actuel">
            <Input
              type="password"
              required
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
            />
          </Field>
          <Field label="Nouveau mot de passe (8 caractères min.)">
            <Input
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </Field>
          <Field label="Confirme le nouveau mot de passe" error={error}>
            <Input
              type="password"
              required
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </Field>
          <Button type="submit" loading={changePassword.isPending}>
            Mettre à jour
          </Button>
        </form>
      </Card>
    </div>
  );
}
