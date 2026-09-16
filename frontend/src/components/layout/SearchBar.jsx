import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { MagnifyingGlass, X, BookOpenText, ChatCircle, Archive, UsersThree, ShieldCheck } from '@phosphor-icons/react';
import { apiGet } from '../../lib/api';

const SECTION_ICONS = {
  courses: BookOpenText,
  community: ChatCircle,
  archives: Archive,
  cohorts: UsersThree,
  spaces: ShieldCheck,
};

const SECTION_ROUTES = {
  courses: (item) => `/courses/${item.id}`,
  community: () => '/community',
  archives: () => '/archives',
  cohorts: (item) => `/cohorts/${item.id}`,
  spaces: () => '/spaces',
};

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);
  const wrapperRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (query.length < 2) {
      setResults(null);
      setOpen(false);
      return;
    }

    setLoading(true);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await apiGet(`/api/search?q=${encodeURIComponent(query)}`);
        setResults(res);
        setOpen(true);
      } catch {
        setResults(null);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const totalResults = results
    ? Object.entries(results).reduce((s, [key, arr]) => {
        // Skip 'total' field which is a number, not an array
        if (key === 'total' || !Array.isArray(arr)) return s;
        return s + arr.length;
      }, 0)
    : 0;

  const handleSelect = (section, item) => {
    const route = SECTION_ROUTES[section]?.(item);
    if (route) {
      navigate(route);
      setOpen(false);
      setQuery('');
    }
  };

  return (
    <div ref={wrapperRef} className="relative w-full max-w-md" data-testid="search-bar">
      <div className="flex items-center gap-2 bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] rounded-md px-3 py-1.5 focus-within:border-[rgb(var(--gold)/0.4)] transition-colors">
        <MagnifyingGlass size={14} weight="bold" className="text-[rgb(var(--text-muted))] flex-shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results && setOpen(true)}
          placeholder="Search courses, posts, archives..."
          className="bg-transparent text-xs text-[rgb(var(--text-main))] placeholder:text-[rgb(var(--text-faint))] outline-none flex-1"
          data-testid="search-input"
        />
        {query && (
          <button onClick={() => { setQuery(''); setOpen(false); }} className="text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-main))]">
            <X size={12} />
          </button>
        )}
        {loading && <div className="w-3 h-3 border border-[rgb(var(--gold))] border-t-transparent rounded-full animate-spin" />}
      </div>

      {/* Dropdown */}
      {open && results && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] rounded-md shadow-xl max-h-80 overflow-y-auto z-50" data-testid="search-results">
          {totalResults === 0 ? (
            <div className="p-4 text-center">
              <p className="text-xs text-[rgb(var(--text-muted))]">No results for "{query}"</p>
            </div>
          ) : (<>
            <button
              onClick={() => { navigate(`/search?q=${encodeURIComponent(query)}`); setOpen(false); setQuery(''); }}
              className="w-full text-left px-3 py-2 text-[10px] text-[rgb(var(--gold))] hover:bg-[rgb(var(--ink-border)/0.5)] transition-colors border-b border-[rgb(var(--ink-border))]"
              data-testid="view-all-results"
            >
              View all {totalResults} results with filters &rarr;
            </button>
            {Object.entries(results).filter(([key]) => key !== 'total').map(([section, items]) => {
              if (!items || !Array.isArray(items) || items.length === 0) return null;
              const Icon = SECTION_ICONS[section] || BookOpenText;
              return (
                <div key={section}>
                  <div className="px-3 py-1.5 bg-[rgb(var(--ink-deep))] border-b border-[rgb(var(--ink-border))]">
                    <div className="flex items-center gap-1.5">
                      <Icon size={11} weight="duotone" className="text-[rgb(var(--gold))]" />
                      <span className="text-[9px] uppercase tracking-widest text-[rgb(var(--gold))]">{section}</span>
                      <span className="text-[9px] text-[rgb(var(--text-faint))]">({items.length})</span>
                    </div>
                  </div>
                  {items.map((item, i) => (
                    <button
                      key={item.id || i}
                      onClick={() => handleSelect(section, item)}
                      className="w-full text-left px-3 py-2 hover:bg-[rgb(var(--ink-border)/0.5)] transition-colors border-b border-[rgb(var(--ink-border)/0.5)] last:border-0"
                      data-testid={`search-result-${section}-${i}`}
                    >
                      <p className="text-xs text-[rgb(var(--text-main))] truncate">{item.title || item.name}</p>
                      {item.description && (
                        <p className="text-[9px] text-[rgb(var(--text-muted))] truncate mt-0.5">{item.description}</p>
                      )}
                    </button>
                  ))}
                </div>
              );
            })}
          </>)}
        </div>
      )}
    </div>
  );
}
