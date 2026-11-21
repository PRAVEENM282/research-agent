import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Task, TaskStatus } from "../api/types";

export type ConnectionState = "connecting" | "live" | "polling" | "closed";

export function useTaskSocket(taskId: string | undefined): ConnectionState {
  const queryClient = useQueryClient();
  const [connection, setConnection] = useState<ConnectionState>("connecting");

  useEffect(() => {
    if (!taskId) return;
    let socket: WebSocket | undefined;
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    let attempt = 0;
    let live = false;

    const updateStatus = (status: TaskStatus) => {
      queryClient.setQueryData<Task>(["task", taskId], (current) => (current ? { ...current, status } : current));
      void queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    };

    const pollTask = async () => {
      if (live || stopped) return;
      try {
        const task = await api.getTask(taskId);
        queryClient.setQueryData(["task", taskId], task);
      } catch {
        // The task query renders the API error; polling stays quiet while the socket retries.
      }
    };

    const connect = () => {
      if (stopped) return;
      const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(`${scheme}//${window.location.host}/ws/tasks/${encodeURIComponent(taskId)}`);
      socket.onopen = () => {
        attempt = 0;
        live = true;
        setConnection("live");
      };
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(String(event.data)) as { task_id?: string; status?: TaskStatus };
          if (message.task_id === taskId && message.status) {
            updateStatus(message.status);
            if (["COMPLETED", "FAILED", "REJECTED"].includes(message.status)) {
              stopped = true;
              live = false;
              setConnection("closed");
              if (poll) clearInterval(poll);
              socket?.close();
            }
          }
        } catch {
          // Malformed events are ignored; the detail query remains authoritative.
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        live = false;
        if (stopped) return;
        setConnection("polling");
        const delay = Math.min(10_000, 800 * 2 ** attempt++);
        reconnect = setTimeout(connect, delay);
      };
    };

    const poll = setInterval(() => void pollTask(), 2_500);
    setConnection("connecting");
    connect();
    return () => {
      stopped = true;
      if (reconnect) clearTimeout(reconnect);
      if (poll) clearInterval(poll);
      socket?.close();
    };
  }, [taskId, queryClient]);

  return connection;
}
