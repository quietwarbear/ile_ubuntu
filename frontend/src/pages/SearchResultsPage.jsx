import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  MagnifyingGlass, BookOpenText, ChatCircle, Archive, UsersThree,
  ShieldCheck, Funnel, SortAscending, X,
} from '@phosphor-icons/react';
import { apiGet } from '../lib/api';

const TYPE_OPTIONS = [
  { value: '', label: 'All Types', icon: MagnifyingGlass },
  { value: 'courses', label: 'Courses', icon: BookOpenText },
  { value: 'community', label: 'Community', icon: ChatCircle },
  { value: 'archives', label: 'Archives', icon: Archive },
  { value: 'cohorts', label: 'Cohorts', icon: UsersThree },
  { value: 'spaces', label: 'Spaces', icon: ShieldCheck },
];

const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'date', label: 'Newest' },
  { value: 'popularity', label: 'Popular' },
];

const SECTION_ROUTES = {
  courses: (item) => `/courses/${item.id}`,
  community: () => '/community',
  archives: () => '/archives',
  cohorts: (item) => `/cohorts/${item.id}`,
  spaces: () => '/spaces',
};

const SECTION_ICONS = {
  courses: BookOpenText,
  community: ChatCircle,
  archives: Archive,
  cohorts: UsersThree,
  spaces: ShieldCheck,
};

export default function SearchResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [typeFilter, setTypeFilter] = useState(searchParams.get('type') || '');
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'relevance');
  const [accessLevel, setAccessLevel] = useState(searchParams.get('access') || '');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const doSearch = useCallback(async () => {
    if (!query || query.length < 2) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ q: query });
      if (typeFilter) params.set('type', typeFilter);
      if (sortBy) params.set('sort', sortBy);
      if (accessLevel) params.set('access_level', accessLevel);
      const res = await apiGet(`/api/search?${params.toString()}`);
      setResults(res);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [query, typeFilter, sortBy, accessLevel]);

  useEffect(() => {
    doSearch();
  }, [doSearch]);

  const handleSearch = (e) => {
    e.preventDefault();
    setSearchParams({ q: query, type: typeFilter, sort: sortBy });
    doSearch();
  };

  const totalResults = results?.total || 0;

  return (
    <div className="space-y-5" data-testid="search-results-page">
      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="flex-1 flex items-center gap-2 bg-[#0F172A] border border-[#1E293B] rounded-md px-3 py-2 focus-within:border-[#D4AF37]/40">
          <MagnifyingGlass size={16} className="text-[#94A3B8]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search across the entire platform..."
            className="bg-transparent text-sm text-[#F8FAFC] outline-none flex-1"
            data-testid="search-page-input"
          />
          {query && (
            <button type="button" onClick={() => { setQuery(''); setResults(null); }} className="text-[#94A3B8] hover:text-[#F8FAFC]">
              <X size={14} />
            </button>
          )}
        </div>
        <button type="submit" className="px-4 py-2 bg-[#D4AF37] text-[#050814] rounded-md text-xs font-medium" data-testid="search-submit">
          Search
        </button>
      </form>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Filters Sidebar */}
        <div className="space-y-3" data-testid="search-filters">
          {/* Type Filter */}
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Funnel size={12} weight="duotone" className="text-[#D4AF37]" />
                <span className="text-[9px] text-[#D4AF37] uppercase tracking-wider">Type</span>
              </div>
              <div className="space-y-1">
                {TYPE_OPTIONS.map(opt => {
                  const Icon = opt.icon;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => { setTypeFilter(opt.value); }}
                      className={`w-full text-left px-2 py-1.5 rounded text-xs flex items-center gap-2 transition-all ${
                        typeFilter === opt.value ? 'bg-[#D4AF37]/10 text-[#D4AF37]' : 'text-[#94A3B8] hover:bg-[#050814]'
                      }`}
                      data-testid={`filter-type-${opt.value || 'all'}`}
                    >
                      <Icon size={12} weight="duotone" /> {opt.label}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Sort */}
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <SortAscending size={12} weight="duotone" className="text-[#D4AF37]" />
                <span className="text-[9px] text-[#D4AF37] uppercase tracking-wider">Sort</span>
              </div>
              <div className="space-y-1">
                {SORT_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setSortBy(opt.value)}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs transition-all ${
                      sortBy === opt.value ? 'bg-[#D4AF37]/10 text-[#D4AF37]' : 'text-[#94A3B8] hover:bg-[#050814]'
                    }`}
                    data-testid={`filter-sort-${opt.value}`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Access Level */}
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <ShieldCheck size={12} weight="duotone" className="text-[#D4AF37]" />
                <span className="text-[9px] text-[#D4AF37] uppercase tracking-wider">Access</span>
              </div>
              <div className="space-y-1">
                {['', 'public', 'restricted', 'members'].map(lvl => (
                  <button
                    key={lvl}
                    onClick={() => setAccessLevel(lvl)}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs transition-all ${
                      accessLevel === lvl ? 'bg-[#D4AF37]/10 text-[#D4AF37]' : 'text-[#94A3B8] hover:bg-[#050814]'
                    }`}
                    data-testid={`filter-access-${lvl || 'all'}`}
                  >
                    {lvl || 'All Access Levels'}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        <div className="md:col-span-3" data-testid="search-results-area">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="w-5 h-5 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : !results ? (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-12 text-center">
                <MagnifyingGlass size={40} weight="duotone" className="text-[#94A3B8] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">Enter a search term to explore the commons</p>
              </CardContent>
            </Card>
          ) : totalResults === 0 ? (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-8 text-center">
                <p className="text-sm text-[#94A3B8]">No results for "{query}"</p>
                <p className="text-xs text-[#475569] mt-1">Try different keywords or clear filters</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-[#94A3B8]">{totalResults} result{totalResults !== 1 ? 's' : ''} for "{query}"</p>

              {Object.entries(results).filter(([k]) => k !== 'total').map(([section, items]) => {
                if (!items || items.length === 0) return null;
                const Icon = SECTION_ICONS[section] || MagnifyingGlass;
                return (
                  <div key={section}>
                    <div className="flex items-center gap-1.5 mb-2">
                      <Icon size={14} weight="duotone" className="text-[#D4AF37]" />
                      <span className="text-[10px] text-[#D4AF37] uppercase tracking-wider">{section}</span>
                      <Badge className="bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20 text-[8px]">{items.length}</Badge>
                    </div>
                    <div className="space-y-1.5">
                      {items.map((item, i) => (
                        <button
                          key={item.id || i}
                          onClick={() => {
                            const route = SECTION_ROUTES[section]?.(item);
                            if (route) navigate(route);
                          }}
                          className="w-full text-left p-3 bg-[#0F172A] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-all"
                          data-testid={`result-${section}-${i}`}
                        >
                          <p className="text-xs text-[#F8FAFC]">{item.title || item.name}</p>
                          {item.description && <p className="text-[9px] text-[#94A3B8] mt-0.5 truncate">{item.description}</p>}
                          <div className="flex gap-2 mt-1">
                            {item.status && <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[7px]">{item.status}</Badge>}
                            {item.access_level && <Badge className="bg-violet-500/10 text-violet-400 border-violet-500/20 text-[7px]">{item.access_level}</Badge>}
                            {item.enrolled_count !== undefined && <span className="text-[8px] text-[#475569]">{item.enrolled_count} enrolled</span>}
                            {item.member_count !== undefined && <span className="text-[8px] text-[#475569]">{item.member_count} members</span>}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
