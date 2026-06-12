import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import {
  useCreateUser,
  useDeleteTraining,
  useReindexTraining,
  useTrainingContents,
  useUpdateTraining,
  useUpdateUser,
  useUploadTraining,
  useUploadTrainingFile,
  useUsers,
} from "../api/hooks";
import type { TrainingContent, UserRole } from "../api/types";
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
  const uploadFileMutation = useUploadTrainingFile();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);

  const pending = uploadMutation.isPending || uploadFileMutation.isPending;
  const error = uploadMutation.error ?? uploadFileMutation.error;

  function resetForm() {
    setTitle("");
    setContent("");
    setFile(null);
    setFileInputKey((k) => k + 1); // remonte l'input file pour le vider
  }

  function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (file) {
      uploadFileMutation.mutate({ title, file }, { onSuccess: resetForm });
    } else {
      uploadMutation.mutate({ title, content }, { onSuccess: resetForm });
    }
  }

  return (
    <section>
      <h2 className="text-lg font-semibold">Contenus de formation</h2>
      <p className="text-sm text-zinc-500">
        Ces documents alimentent l'agent d'entraînement de tes commerciaux (RAG). Un document{" "}
        <span className="text-emerald-600">indexé</span> est vectorisé et utilisable par l'agent ;{" "}
        <span className="text-amber-600">non indexé</span> signifie que l'indexation a échoué
        (service d'embeddings indisponible au moment de l'upload) — utilise « Réindexer ».
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
        <div className="flex items-center gap-2">
          <input
            key={fileInputKey}
            type="file"
            accept=".pdf,.txt,.md,application/pdf,text/plain"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-zinc-600 file:mr-3 file:rounded-md file:border-0 file:bg-zinc-100 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-zinc-200"
          />
          {file && (
            <button
              type="button"
              onClick={() => {
                setFile(null);
                setFileInputKey((k) => k + 1);
              }}
              className="text-xs text-zinc-500 hover:text-zinc-800"
            >
              Retirer le fichier
            </button>
          )}
        </div>
        <textarea
          required={!file}
          disabled={file !== null}
          minLength={20}
          rows={5}
          placeholder={
            file
              ? "Le contenu sera extrait du fichier sélectionné"
              : "… ou colle ici le contenu texte (argumentaire, fiche produit, tarifs…)"
          }
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:bg-zinc-50 disabled:text-zinc-400"
        />
        {error && (
          <p className="text-sm text-red-600">
            {error instanceof ApiError ? error.message : "Upload impossible"}
          </p>
        )}
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
        >
          {pending ? "Traitement…" : "Ajouter le document"}
        </button>
      </form>

      {trainingQuery.isLoading && <p className="mt-3 text-sm text-zinc-500">Chargement…</p>}
      {trainingQuery.isSuccess && (trainingQuery.data ?? []).length === 0 && (
        <p className="mt-3 text-sm text-zinc-500">Aucun document pour l'instant.</p>
      )}

      <ul className="mt-3 space-y-2">
        {(trainingQuery.data ?? []).map((doc) => (
          <TrainingItem key={doc.id} doc={doc} />
        ))}
      </ul>
    </section>
  );
}

function TrainingItem({ doc }: { doc: TrainingContent }) {
  const updateMutation = useUpdateTraining();
  const reindexMutation = useReindexTraining();
  const deleteMutation = useDeleteTraining();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(doc.title);
  const [content, setContent] = useState(doc.raw_content);

  function handleSave(event: FormEvent) {
    event.preventDefault();
    updateMutation.mutate(
      { contentId: doc.id, title, content },
      { onSuccess: () => setEditing(false) },
    );
  }

  return (
    <li className="rounded-lg border border-zinc-200 bg-white px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium">{doc.title}</p>
          <p className="text-xs text-zinc-500">
            {formatDate(doc.created_at)} · {doc.content_type.toUpperCase()} ·{" "}
            {doc.chunk_metadata.chunk_count ?? "?"} segment(s) ·{" "}
            {doc.is_embedded ? (
              <span className="text-emerald-600">indexé</span>
            ) : (
              <span className="text-amber-600">non indexé</span>
            )}
          </p>
        </div>
        <div className="flex shrink-0 gap-2 text-sm">
          {!doc.is_embedded && (
            <button
              onClick={() => reindexMutation.mutate(doc.id)}
              disabled={reindexMutation.isPending}
              className="rounded-md border border-amber-300 px-2 py-1 text-amber-700 hover:bg-amber-50 disabled:opacity-50"
            >
              {reindexMutation.isPending ? "Indexation…" : "Réindexer"}
            </button>
          )}
          <button
            onClick={() => {
              setTitle(doc.title);
              setContent(doc.raw_content);
              setEditing((e) => !e);
            }}
            className="rounded-md border border-zinc-300 px-2 py-1 text-zinc-600 hover:bg-zinc-100"
          >
            {editing ? "Annuler" : "Modifier"}
          </button>
          <button
            onClick={() => deleteMutation.mutate(doc.id)}
            className="rounded-md border border-red-200 px-2 py-1 text-red-600 hover:bg-red-50"
          >
            Supprimer
          </button>
        </div>
      </div>

      {reindexMutation.isError && (
        <p className="mt-2 text-sm text-red-600">
          {reindexMutation.error instanceof ApiError
            ? reindexMutation.error.message
            : "Réindexation impossible"}
        </p>
      )}

      {editing && (
        <form onSubmit={handleSave} className="mt-3 space-y-2 border-t border-zinc-100 pt-3">
          <input
            required
            minLength={2}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          />
          <textarea
            required
            minLength={20}
            rows={6}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          />
          {updateMutation.isError && (
            <p className="text-sm text-red-600">
              {updateMutation.error instanceof ApiError
                ? updateMutation.error.message
                : "Modification impossible"}
            </p>
          )}
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
          >
            {updateMutation.isPending ? "Enregistrement…" : "Enregistrer (réindexe le contenu)"}
          </button>
        </form>
      )}
    </li>
  );
}
