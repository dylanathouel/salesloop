import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import {
  useCreateUser,
  useDeleteTraining,
  useTrainingContents,
  useUpdateUser,
  useUploadTraining,
  useUsers,
} from "../api/hooks";
import type { UserRole } from "../api/types";
import { formatDate } from "../utils/format";

const ROLE_LABELS: Record<UserRole, string> = {
  commercial: "Commercial",
  manager: "Manager",
  direction: "Direction",
};

export function AdminPage() {
  return (
    <div className="mx-auto h-full max-w-6xl space-y-8 overflow-y-auto p-6">
      <UsersSection />
      <TrainingSection />
    </div>
  );
}

// --- Users -------------------------------------------------------------

function UsersSection() {
  const usersQuery = useUsers();
  const createMutation = useCreateUser();
  const updateMutation = useUpdateUser();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: "commercial" as UserRole,
    manager_id: "",
  });

  const users = usersQuery.data ?? [];
  const managers = users.filter((u) => u.role === "manager");

  function handleCreate(event: FormEvent) {
    event.preventDefault();
    createMutation.mutate(
      {
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        role: form.role,
        manager_id: form.role === "commercial" && form.manager_id ? form.manager_id : null,
      },
      {
        onSuccess: () =>
          setForm({ full_name: "", email: "", password: "", role: "commercial", manager_id: "" }),
      },
    );
  }

  return (
    <section>
      <h2 className="text-lg font-semibold">Utilisateurs</h2>

      <form
        onSubmit={handleCreate}
        className="mt-3 grid gap-2 rounded-lg border border-zinc-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-6"
      >
        <input
          required
          placeholder="Nom complet"
          value={form.full_name}
          onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
        />
        <input
          required
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
        />
        <input
          required
          type="password"
          minLength={8}
          placeholder="Mot de passe"
          value={form.password}
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
        />
        <select
          value={form.role}
          onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as UserRole }))}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
        >
          {Object.entries(ROLE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={form.manager_id}
          onChange={(e) => setForm((f) => ({ ...f, manager_id: e.target.value }))}
          disabled={form.role !== "commercial"}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:bg-zinc-100"
        >
          <option value="">Sans manager</option>
          {managers.map((manager) => (
            <option key={manager.id} value={manager.id}>
              {manager.full_name}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
        >
          Créer
        </button>
        {createMutation.isError && (
          <p className="col-span-full text-sm text-red-600">
            {createMutation.error instanceof ApiError
              ? createMutation.error.message
              : "Création impossible"}
          </p>
        )}
      </form>

      <div className="mt-3 overflow-x-auto rounded-lg border border-zinc-200 bg-white">
        {usersQuery.isLoading && <p className="p-4 text-sm text-zinc-500">Chargement…</p>}
        {usersQuery.isError && (
          <p className="p-4 text-sm text-red-600">Impossible de charger les utilisateurs</p>
        )}
        {users.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-xs uppercase text-zinc-500">
                <th className="px-4 py-3">Nom</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Rôle</th>
                <th className="px-4 py-3">Manager</th>
                <th className="px-4 py-3">Statut</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-zinc-100 last:border-0">
                  <td className="px-4 py-3 font-medium">{user.full_name}</td>
                  <td className="px-4 py-3 text-zinc-600">{user.email}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs">
                      {ROLE_LABELS[user.role]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {user.role === "commercial" ? (
                      <select
                        value={user.manager_id ?? ""}
                        onChange={(e) =>
                          updateMutation.mutate({
                            userId: user.id,
                            manager_id: e.target.value || null,
                          })
                        }
                        className="rounded-md border border-zinc-200 px-2 py-1 text-xs"
                      >
                        <option value="">Sans manager</option>
                        {managers.map((manager) => (
                          <option key={manager.id} value={manager.id}>
                            {manager.full_name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-zinc-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        updateMutation.mutate({ userId: user.id, is_active: !user.is_active })
                      }
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        user.is_active
                          ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                          : "bg-red-100 text-red-700 hover:bg-red-200"
                      }`}
                    >
                      {user.is_active ? "Actif" : "Désactivé"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// --- Training ------------------------------------------------------------

function TrainingSection() {
  const trainingQuery = useTrainingContents();
  const uploadMutation = useUploadTraining();
  const deleteMutation = useDeleteTraining();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  function handleUpload(event: FormEvent) {
    event.preventDefault();
    uploadMutation.mutate(
      { title, content },
      {
        onSuccess: () => {
          setTitle("");
          setContent("");
        },
      },
    );
  }

  return (
    <section>
      <h2 className="text-lg font-semibold">Contenus de formation</h2>
      <p className="text-sm text-zinc-500">
        Ces documents alimentent l'agent d'entraînement de tes commerciaux (RAG).
      </p>

      <form
        onSubmit={handleUpload}
        className="mt-3 space-y-2 rounded-lg border border-zinc-200 bg-white p-4"
      >
        <input
          required
          minLength={2}
          placeholder="Titre du document"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
        />
        <textarea
          required
          minLength={20}
          rows={5}
          placeholder="Colle ici le contenu texte (argumentaire, fiche produit, politique tarifaire…)"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
        />
        {uploadMutation.isError && (
          <p className="text-sm text-red-600">
            {uploadMutation.error instanceof ApiError
              ? uploadMutation.error.message
              : "Upload impossible"}
          </p>
        )}
        <button
          type="submit"
          disabled={uploadMutation.isPending}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
        >
          {uploadMutation.isPending ? "Traitement…" : "Ajouter le document"}
        </button>
      </form>

      {trainingQuery.isLoading && <p className="mt-3 text-sm text-zinc-500">Chargement…</p>}
      {trainingQuery.isSuccess && (trainingQuery.data ?? []).length === 0 && (
        <p className="mt-3 text-sm text-zinc-500">Aucun document pour l'instant.</p>
      )}

      <ul className="mt-3 space-y-2">
        {(trainingQuery.data ?? []).map((doc) => (
          <li
            key={doc.id}
            className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-4 py-3"
          >
            <div>
              <p className="text-sm font-medium">{doc.title}</p>
              <p className="text-xs text-zinc-500">
                {formatDate(doc.created_at)} · {doc.chunk_metadata.chunk_count ?? "?"} segment(s) ·{" "}
                {doc.is_embedded ? (
                  <span className="text-emerald-600">indexé</span>
                ) : (
                  <span className="text-amber-600">non indexé</span>
                )}
              </p>
            </div>
            <button
              onClick={() => deleteMutation.mutate(doc.id)}
              className="rounded-md border border-red-200 px-2 py-1 text-sm text-red-600 hover:bg-red-50"
            >
              Supprimer
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
