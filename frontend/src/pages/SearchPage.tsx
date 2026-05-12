import { Search } from "lucide-react";
import { useState } from "react";
import { SectionHeader } from "../components/SectionHeader";
import { api } from "../lib/api";
import type { SearchResult } from "../types";

type Props = {
  token: string;
};

export function SearchPage({ token }: Props) {
  const [query, setQuery] = useState("");
  const [sourceTypes, setSourceTypes] = useState(["journal", "note"]);
  const [results, setResults] = useState<SearchResult[]>([]);

  async function runSearch() {
    if (!query.trim()) return;
    const response = await api.search(token, query, sourceTypes);
    setResults(response.results);
  }

  function toggle(type: string) {
    setSourceTypes((current) => current.includes(type) ? current.filter((item) => item !== type) : [...current, type]);
  }

  return (
    <section>
      <SectionHeader eyebrow="Recall" title="Semantic search" description="Ask in natural language and retrieve relevant journal and note chunks from Qdrant." />
      <div className="glass-panel rounded-2xl p-4">
        <div className="flex flex-col gap-3 md:flex-row">
          <input className="control" placeholder="Search your memory..." value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void runSearch()} />
          <button className="button-primary md:w-40" onClick={() => void runSearch()}>
            <Search size={16} />
            Search
          </button>
        </div>
        <div className="mt-3 flex gap-2">
          {["journal", "note"].map((type) => (
            <button key={type} onClick={() => toggle(type)} className={`badge ${sourceTypes.includes(type) ? "border-mint/50 text-mint" : ""}`}>
              {type}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 grid gap-4">
        {results.map((result) => (
          <article key={`${result.source_type}-${result.source_id}-${result.score}`} className="glass-panel rounded-2xl p-5">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-semibold">{result.title || result.source_type}</h2>
              <span className="badge">{result.score.toFixed(3)}</span>
            </div>
            <p className="text-sm leading-6 text-white/60">{result.snippet}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
