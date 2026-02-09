/**
 * Offline layer: Dexie DB for artifacts and pending mutations queue.
 * Sync queue retries in order when online; last-write-wins; surface conflict on 409.
 */

import Dexie, { type Table } from "dexie";

export interface LocalArtifactDraft {
  id: string;
  artifactId: string;
  projectId: string;
  title: string | null;
  content: string;
  updatedAt: number;
}

export interface SyncQueueItem {
  id?: number;
  method: string;
  path: string;
  body?: string;
  createdAt: number;
  retryCount: number;
  lastError?: string;
  status: "pending" | "conflict" | "failed";
}

class VivaOfflineDB extends Dexie {
  artifactDrafts!: Table<LocalArtifactDraft, string>;
  syncQueue!: Table<SyncQueueItem, number>;

  constructor() {
    super("VivaOfflineDB");
    this.version(1).stores({
      artifactDrafts: "id, artifactId, projectId, updatedAt",
      syncQueue: "++id, createdAt, status",
    });
  }
}

export const db = new VivaOfflineDB();

export async function saveDraft(
  artifactId: string,
  projectId: string,
  data: { title: string | null; content: string }
): Promise<void> {
  const id = `draft-${artifactId}`;
  await db.artifactDrafts.put({
    id,
    artifactId,
    projectId,
    title: data.title,
    content: data.content,
    updatedAt: Date.now(),
  });
}

export async function getDraft(artifactId: string): Promise<LocalArtifactDraft | undefined> {
  return db.artifactDrafts.get(`draft-${artifactId}`);
}

export async function clearDraft(artifactId: string): Promise<void> {
  await db.artifactDrafts.delete(`draft-${artifactId}`);
}

export async function getDraftsForProject(projectId: string): Promise<LocalArtifactDraft[]> {
  return db.artifactDrafts.where("projectId").equals(projectId).toArray();
}

export function enqueueMutation(method: string, path: string, body?: unknown): void {
  db.syncQueue.add({
    method,
    path,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    createdAt: Date.now(),
    retryCount: 0,
    status: "pending",
  });
}

export async function getPendingQueueCount(): Promise<number> {
  return db.syncQueue.where("status").equals("pending").count();
}

export async function getPendingQueue(): Promise<SyncQueueItem[]> {
  return db.syncQueue.where("status").equals("pending").sortBy("createdAt");
}

export async function markQueueItemConflict(id: number, message: string): Promise<void> {
  await db.syncQueue.update(id, { status: "conflict", lastError: message });
}

export async function markQueueItemFailed(id: number, message: string): Promise<void> {
  await db.syncQueue.update(id, { status: "failed", lastError: message });
}

export async function deleteQueueItem(id: number): Promise<void> {
  await db.syncQueue.delete(id);
}

/**
 * Process sync queue: for each pending item, call the provided executor.
 * Executor returns { ok: true } or { ok: false, status, body }.
 * On 409 we mark conflict; on other failure we mark failed (or retry later).
 */
export async function processSyncQueue(
  executor: (item: SyncQueueItem) => Promise<{ ok: boolean; status?: number; body?: unknown }>
): Promise<{ processed: number; conflicts: number }> {
  const items = await getPendingQueue();
  let processed = 0;
  let conflicts = 0;
  for (const item of items) {
    if (item.id === undefined) continue;
    try {
      const result = await executor(item);
      if (result.ok) {
        await deleteQueueItem(item.id);
        processed++;
      } else {
        if (result.status === 409) {
          await markQueueItemConflict(
            item.id,
            typeof result.body === "object" && result.body && "detail" in result.body
              ? String((result.body as { detail: unknown }).detail)
              : "Conflict"
          );
          conflicts++;
        } else {
          await markQueueItemFailed(
            item.id,
            typeof result.body === "object" && result.body && "detail" in result.body
              ? String((result.body as { detail: unknown }).detail)
              : "Request failed"
          );
        }
      }
    } catch (e) {
      await markQueueItemFailed(item.id, e instanceof Error ? e.message : "Network error");
    }
  }
  return { processed, conflicts };
}
