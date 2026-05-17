import { useCallback, useEffect, useMemo, useState } from "react";
import { api, AUTH_EXPIRED_EVENT, isUnauthorizedError } from "../lib/api";
import type { ConversationSummary, DocumentResource, Journal, Note, SearchResult, User } from "../types";

const TOKEN_KEY = "mindmesh.token";
const USER_KEY = "mindmesh.user";
const SESSION_LOCK_KEY = "mindmesh.sessionLocked";

export function useMindMesh() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as User;
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      return null;
    }
  });
  const [journals, setJournals] = useState<Journal[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [documents, setDocuments] = useState<DocumentResource[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [tags, setTags] = useState<Array<{ id: string; name: string }>>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const authenticated = Boolean(token && user);

  const client = useMemo(() => ({ token }), [token]);

  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
    setJournals([]);
    setNotes([]);
    setDocuments([]);
    setConversations([]);
    setTags([]);
    setSearchResults([]);
    setError(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(SESSION_LOCK_KEY);
  }, []);

  const setSession = useCallback((nextToken: string, nextUser: User) => {
    setToken(nextToken);
    setUser(nextUser);
    setError(null);
    localStorage.setItem(TOKEN_KEY, nextToken);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
  }, []);

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const run = useCallback(async <T,>(operation: () => Promise<T>) => {
    setLoading(true);
    setError(null);
    try {
      return await operation();
    } catch (err) {
      if (isUnauthorizedError(err)) {
        clearSession();
        return undefined as T;
      }
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [clearSession]);

  const refresh = useCallback(async () => {
    if (!token) return;
    await run(async () => {
      const [nextJournals, nextNotes, nextDocuments, nextTags, nextConversations] = await Promise.all([
        api.journals(token),
        api.notes(token),
        api.documents(token),
        api.tags(token),
        api.conversations(token)
      ]);
      setJournals(nextJournals);
      setNotes(nextNotes);
      setDocuments(nextDocuments);
      setTags(nextTags);
      setConversations(nextConversations);
    });
  }, [run, token]);

  useEffect(() => {
    void refresh().catch(() => undefined);
  }, [refresh]);

  useEffect(() => {
    const handleAuthExpired = () => {
      clearSession();
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    };
  }, [clearSession]);

  return {
    ...client,
    user,
    authenticated,
    journals,
    notes,
    documents,
    conversations,
    tags,
    searchResults,
    loading,
    error,
    setError,
    setSession,
    logout,
    refresh,
    run,
    setJournals,
    setNotes,
    setDocuments,
    setConversations,
    setSearchResults
  };
}
