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
import { Badge, type BadgeTone } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Field, Input, Select, Textarea } from "../components/ui/Field";
import { FileText, RefreshCw, Upload } from "../components/ui/icons";
import { SkeletonRows } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { formatDate } from "../utils/format";

const ROLE_LABELS: Record<UserRole, string> = {
  commercial: "Commercial",
  manager: "Manager",
  direction: "Direction",
};

const ROLE_TONES: Record<UserRole, BadgeTone> = {
  commercial: "blue",
  manager: "amber",
  direction: "emerald",
};

export function AdminPage() {
  return (
    <div className="mx-auto h-full max-w-6xl space-y-8 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Administration</h1>
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
  const toast = useToast();
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
        onSuccess: () => {
          setForm({ full_name: "", email: "", password: "", role: "commercial", manager_id: "" });
          toast.success("Compte créé");
        },
        onError: (err) =>
          toast.error(err instanceof ApiError ? err.message : "Création impossible"),
      },
    );
  }

  return (
    <section>
      <h2 className="text-lg font-semibold">Utilisateurs</h2>

      <Card className="mt-3 p-4">
        <form onSubmit={handleCreate} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
          <Input
            required
            placeholder="Nom complet"
            value={form.full_name}
            onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
          />
          <Input
            required
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          />
          <Input
            required
            type="password"
            minLength={8}
            placeholder="Mot de passe"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          />
          <Select
            value={form.role}
            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as UserRole }))}
          >
            {Object.entries(ROLE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <Select
            value={form.manager_id}
            onChange={(e) => setForm((f) => ({ ...f, manager_id: e.target.value }))}
            disabled={form.role !== "commercial"}
          >
            <option value="">Sans manager</option>
            {managers.map((manager) => (
              <option key={manager.id} value={manager.id}>
                {manager.full_name}
              </option>
            ))}
          </Select>
          <Button type="submit" loading={createMutation.isPending}>
            Créer
          </Button>
        </form>
      </Card>

      <Card className="mt-3 overflow-hidden">
        {usersQuery.isLoading && <div className="p-3"><SkeletonRows rows={4} /></div>}
        {usersQuery.isError && (
          <p className="p-4 text-sm text-red-600 dark:text-red-400">
            Impossible de charger les utilisateurs
          </p>
        )}
        {users.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-xs uppercase text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                <th className="px-4 py-3">Nom</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Rôle</th>
                <th className="px-4 py-3">Manager</th>
                <th className="px-4 py-3">Statut</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  key={user.id}
                  className="border-b border-zinc-100 last:border-0 dark:border-zinc-800"
                >
                  <td className="px-4 py-3 font-medium">{user.full_name}</td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{user.email}</td>
                  <td className="px-4 py-3">
                    <Badge tone={ROLE_TONES[user.role]}>{ROLE_LABELS[user.role]}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    {user.role === "commercial" ? (
                      <Select
                        value={user.manager_id ?? ""}
                        onChange={(e) =>
                          updateMutation.mutate({
                            userId: user.id,
                            manager_id: e.target.value || null,
                          })
                        }
                        className="w-auto text-xs"
                      >
                        <option value="">Sans manager</option>
                        {managers.map((manager) => (
                          <option key={manager.id} value={manager.id}>
                            {manager.full_name}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      <span className="text-zinc-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        updateMutation.mutate({ userId: user.id, is_active: !user.is_active })
                      }
                    >
                      <Badge tone={user.is_active ? "emerald" : "red"}>
                        {user.is_active ? "Actif" : "Désactivé"}
                      </Badge>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </section>
  );
}

// --- Training ------------------------------------------------------------

function TrainingSection() {
  const trainingQuery = useTrainingContents();
  const uploadMutation = useUploadTraining();
  const uploadFileMutation = useUploadTrainingFile();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);

  const pending = uploadMutation.isPending || uploadFileMutation.isPending;

  function resetForm() {
    setTitle("");
    setContent("");
    setFile(null);
    setFileInputKey((k) => k + 1);
  }

  function handleUpload(event: FormEvent) {
    event.preventDefault();
    const onSuccess = () => {
      resetForm();
      toast.success("Document ajouté");
    };
    const onError = (err: unknown) =>
      toast.error(err instanceof ApiError ? err.message : "Upload impossible");
    if (file) {
      uploadFileMutation.mutate({ title, file }, { onSuccess, onError });
    } else {
      uploadMutation.mutate({ title, content }, { onSuccess, onError });
    }
  }

  return (
    <section>
      <h2 className="text-lg font-semibold">Contenus de formation</h2>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        Ces documents alimentent l'agent d'entraînement de tes commerciaux (RAG). Un document{" "}
        <span className="text-emerald-600 dark:text-emerald-400">indexé</span> est vectorisé et
        utilisable par l'agent ; <span className="text-amber-600 dark:text-amber-400">non indexé</span>{" "}
        signifie que l'indexation a échoué (service d'embeddings indisponible) — utilise « Réindexer ».
      </p>

      <Card className="mt-3 p-4">
        <form onSubmit={handleUpload} className="space-y-2">
          <Input
            required
            minLength={2}
            placeholder="Titre du document"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <input
              key={fileInputKey}
              type="file"
              accept=".pdf,.txt,.md,application/pdf,text/plain"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-sm text-zinc-600 file:mr-3 file:rounded-md file:border-0 file:bg-zinc-100 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-zinc-200 dark:text-zinc-400 dark:file:bg-zinc-800 dark:hover:file:bg-zinc-700"
            />
            {file && (
              <button
                type="button"
                onClick={() => {
                  setFile(null);
                  setFileInputKey((k) => k + 1);
                }}
                className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
              >
                Retirer le fichier
              </button>
            )}
          </div>
          <Textarea
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
          />
          <Button type="submit" loading={pending} icon={<Upload className="h-4 w-4" />}>
            Ajouter le document
          </Button>
        </form>
      </Card>

      {trainingQuery.isLoading && <div className="mt-3"><SkeletonRows rows={3} /></div>}
      {trainingQuery.isSuccess && (trainingQuery.data ?? []).length === 0 && (
        <EmptyState icon={FileText} title="Aucun document" description="Ajoute un premier contenu de formation." />
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
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(doc.title);
  const [content, setContent] = useState(doc.raw_content);

  function handleSave(event: FormEvent) {
    event.preventDefault();
    updateMutation.mutate(
      { contentId: doc.id, title, content },
      {
        onSuccess: () => {
          setEditing(false);
          toast.success("Document mis à jour");
        },
        onError: (err) =>
          toast.error(err instanceof ApiError ? err.message : "Modification impossible"),
      },
    );
  }

  return (
    <Card className="px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium">{doc.title}</p>
          <p className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
            {formatDate(doc.created_at)} · {doc.content_type.toUpperCase()} ·{" "}
            {doc.chunk_metadata.chunk_count ?? "?"} segment(s)
            <Badge tone={doc.is_embedded ? "emerald" : "amber"}>
              {doc.is_embedded ? "indexé" : "non indexé"}
            </Badge>
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          {!doc.is_embedded && (
            <Button
              variant="secondary"
              size="sm"
              loading={reindexMutation.isPending}
              icon={<RefreshCw className="h-3.5 w-3.5" />}
              onClick={() =>
                reindexMutation.mutate(doc.id, {
                  onSuccess: () => toast.success("Document réindexé"),
                  onError: (err) =>
                    toast.error(err instanceof ApiError ? err.message : "Réindexation impossible"),
                })
              }
            >
              Réindexer
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setTitle(doc.title);
              setContent(doc.raw_content);
              setEditing((e) => !e);
            }}
          >
            {editing ? "Annuler" : "Modifier"}
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() =>
              deleteMutation.mutate(doc.id, {
                onSuccess: () => toast.success("Document supprimé"),
              })
            }
          >
            Supprimer
          </Button>
        </div>
      </div>

      {editing && (
        <form onSubmit={handleSave} className="mt-3 space-y-2 border-t border-zinc-100 pt-3 dark:border-zinc-800">
          <Field label="Titre">
            <Input
              required
              minLength={2}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>
          <Field label="Contenu">
            <Textarea
              required
              minLength={20}
              rows={6}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </Field>
          <Button type="submit" loading={updateMutation.isPending}>
            Enregistrer (réindexe le contenu)
          </Button>
        </form>
      )}
    </Card>
  );
}
