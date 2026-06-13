// All data-fetching goes through TanStack Query hooks (no ad-hoc useEffect).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, apiUpload } from "./client";
import type {
  AgentType,
  Conversation,
  ConversationStart,
  Directive,
  DirectivePriority,
  DirectiveStatus,
  Message,
  Report,
  ReportPeriodType,
  TrainingContent,
  User,
  UserRole,
} from "./types";

// --- Users -------------------------------------------------------------

export function useUsers(enabled = true) {
  return useQuery({
    queryKey: ["users"],
    queryFn: () => api<User[]>("/users/"),
    enabled,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      email: string;
      password: string;
      full_name: string;
      role: UserRole;
      manager_id?: string | null;
    }) => api<User>("/auth/users", { method: "POST", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      ...body
    }: {
      userId: string;
      is_active?: boolean;
      manager_id?: string | null;
    }) => api<User>(`/users/${userId}`, { method: "PATCH", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { old_password: string; new_password: string }) =>
      api<void>("/users/me/password", { method: "POST", body }),
  });
}

// --- Conversations -----------------------------------------------------

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: () => api<Conversation[]>("/conversations/"),
  });
}

export function useMessages(conversationId: string | null) {
  return useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => api<Message[]>(`/conversations/${conversationId}/messages`),
    enabled: conversationId !== null,
  });
}

export function useStartConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentType: AgentType) =>
      api<ConversationStart>("/conversations/", {
        method: "POST",
        body: { agent_type: agentType },
      }),
    onSuccess: (conversation) => {
      if (conversation.first_message) {
        queryClient.setQueryData<Message[]>(
          ["messages", conversation.id],
          [conversation.first_message],
        );
      }
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}

export function useSendMessage(conversationId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) =>
      api<Message[]>(`/conversations/${conversationId}/messages`, {
        method: "POST",
        body: { content },
      }),
    onSuccess: (newMessages) => {
      queryClient.setQueryData<Message[]>(["messages", conversationId], (old = []) => [
        ...old,
        ...newMessages,
      ]);
    },
  });
}

export function useCloseConversation(conversationId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api<Conversation>(`/conversations/${conversationId}/close`, { method: "POST" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

// --- Directives ----------------------------------------------------------

export function useDirectives() {
  return useQuery({
    queryKey: ["directives"],
    queryFn: () => api<Directive[]>("/directives/"),
  });
}

export function useCreateDirective() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { content: string; priority: DirectivePriority }) =>
      api<Directive>("/directives/", { method: "POST", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["directives"] }),
  });
}

export function useUpdateDirective() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ directiveId, ...body }: { directiveId: string; status?: DirectiveStatus }) =>
      api<Directive>(`/directives/${directiveId}`, { method: "PATCH", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["directives"] }),
  });
}

export function useDeleteDirective() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (directiveId: string) =>
      api<void>(`/directives/${directiveId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["directives"] }),
  });
}

// --- Reports -------------------------------------------------------------

export function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: () => api<Report[]>("/reports/"),
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      period_type: ReportPeriodType;
      period_start: string;
      period_end: string;
    }) => api<Report>("/reports/generate", { method: "POST", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });
}

// --- Training ------------------------------------------------------------

export function useTrainingContents() {
  return useQuery({
    queryKey: ["training"],
    queryFn: () => api<TrainingContent[]>("/training/"),
  });
}

export function useUploadTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; content: string }) =>
      api<TrainingContent>("/training/", { method: "POST", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training"] }),
  });
}

export function useUploadTrainingFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ title, file }: { title: string; file: File }) => {
      const formData = new FormData();
      formData.append("title", title);
      formData.append("file", file);
      return apiUpload<TrainingContent>("/training/upload", formData);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training"] }),
  });
}

export function useUpdateTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentId,
      ...body
    }: {
      contentId: string;
      title?: string;
      content?: string;
    }) => api<TrainingContent>(`/training/${contentId}`, { method: "PATCH", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training"] }),
  });
}

export function useReindexTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contentId: string) =>
      api<TrainingContent>(`/training/${contentId}/reindex`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training"] }),
  });
}

export function useDeleteTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contentId: string) => api<void>(`/training/${contentId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training"] }),
  });
}
