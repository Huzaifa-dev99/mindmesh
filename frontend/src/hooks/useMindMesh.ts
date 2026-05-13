import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { ConversationSummary, DocumentResource, Journal, Note, SearchResult, User } from "../types";

const TOKEN_KEY = "mindmesh.token";
const USER_KEY = "mindmesh.user";

export function useMindMesh() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
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

  const setSession = useCallback((nextToken: string, nextUser: User) => {
    setToken(nextToken);
    setUser(nextUser);
    localStorage.setItem(TOKEN_KEY, nextToken);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setJournals([]);
    setNotes([]);
    setDocuments([]);
    setConversations([]);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  const run = useCallback(async <T,>(operation: () => Promise<T>) => {
    setLoading(true);
    setError(null);
    try {
      return await operation();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

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
    void refresh();
  }, [refresh]);

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
