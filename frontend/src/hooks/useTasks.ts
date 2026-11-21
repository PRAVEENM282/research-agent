import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useTasks(status?: string, limit = 25, offset = 0) {
  return useQuery({ queryKey: ["tasks", status, limit, offset], queryFn: () => api.listTasks({ status, limit, offset }) });
}

export function useTask(id: string | undefined) {
  return useQuery({
    queryKey: ["task", id],
    queryFn: () => api.getTask(id!),
    enabled: Boolean(id),
    staleTime: 1_000,
  });
}
