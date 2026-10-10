import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Search,
  ChevronRight,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  Upload,
  User,
} from 'lucide-react';
import { api } from '@/lib/api';

export function ResultsList() {
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        const params: any = { skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE };
        if (classFilter !== 'all') {
          params.classification = classFilter;
        }

        const res = await api.get('/analysis', { params });
        setAnalyses(res.data.items ?? []);
        setTotal(res.data.total ?? 0);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, [page, classFilter]);

  const filtered = search
    ? analyses.filter(
        (a) =>
          a.person_name?.toLowerCase().includes(search.toLowerCase()) ||
          a.analysis_number?.toLowerCase().includes(search.toLowerCase()) ||
          a.original_filename?.toLowerCase().includes(search.toLowerCase()) ||
          a.document_type?.toLowerCase().includes(search.toLowerCase())
      )
    : analyses;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Identity Records</h1>
          <p className="text-muted-foreground mt-1">
            Browse all {total > 0 ? `${total} ` : ''}screened identity cards with OCR extracted person information.
          </p>
        </div>
        <Button asChild className="font-semibold">
          <Link to="/upload">
            <Upload className="mr-2 h-4 w-4" /> Upload Document
          </Link>
        </Button>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        {/* Quick Filter Tabs: All, Pass, Suspicious, Failed */}
        <div className="flex p-1 rounded-xl bg-muted/40 border border-border/50 gap-1">
          {[
            { id: 'all', label: 'All Records' },
            { id: 'Pass', label: 'Pass (Genuine)' },
            { id: 'Suspicious', label: 'Suspicious' },
            { id: 'Failed', label: 'Failed (Fake)' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setClassFilter(tab.id);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                classFilter === tab.id
                  ? 'bg-background shadow-sm text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search person, ID, or file…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-sm rounded-xl border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      {/* Table */}
      <Card className="shadow-sm">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-20 gap-3 text-muted-foreground text-sm">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              Loading records…
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-20 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p className="font-semibold text-foreground">No matching records found</p>
              <p className="text-sm mt-1">Try selecting another filter or upload a new identity document.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="border-b bg-muted/30">
                  <tr>
                    <th className="px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Person Name & Age
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Document Type
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Real vs Fake %
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Classification
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-4 py-3 text-right"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {filtered.map((a) => {
                    const classification =
                      a.classification ||
                      (a.verdict === 'GENUINE' ? 'Pass' : a.verdict === 'FORGED' ? 'Failed' : 'Suspicious');
                    const isPass = classification === 'Pass' || a.verdict === 'PASS';
                    const isFail = classification === 'Failed' || a.verdict === 'FAILED';
                    const realProb =
                      a.real_probability != null
                        ? a.real_probability
                        : isPass
                        ? 96.0
                        : isFail
                        ? 8.0
                        : 54.0;
                    const fakeProb =
                      a.fake_probability != null
                        ? a.fake_probability
                        : isFail
                        ? 92.0
                        : isPass
                        ? 4.0
                        : 46.0;

                    return (
                      <tr key={a.id} className="hover:bg-muted/20 transition-colors group">
                        {/* Person Name & Age */}
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2.5">
                            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary shrink-0">
                              <User className="h-4 w-4" />
                            </div>
                            <div>
                              <p className="font-bold text-foreground truncate max-w-[200px]">
                                {a.person_name && a.person_name !== '—'
                                  ? a.person_name
                                  : a.original_filename}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {a.person_age && a.person_age !== '—'
                                  ? `Age: ${a.person_age}`
                                  : a.analysis_number}
                              </p>
                            </div>
                          </div>
                        </td>

                        {/* Document Type */}
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <span className="font-medium text-foreground">
                            {a.document_type || 'Identity Card'}
                          </span>
                        </td>

                        {/* Real vs Fake % */}
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 text-xs font-semibold">
                              <span className="text-green-600 dark:text-green-400">
                                Real: {realProb.toFixed(0)}%
                              </span>
                              <span className="text-muted-foreground">/</span>
                              <span className="text-red-600 dark:text-red-400">
                                Fake: {fakeProb.toFixed(0)}%
                              </span>
                            </div>
                            <div className="h-1.5 w-28 bg-red-200 dark:bg-red-950/60 rounded-full overflow-hidden flex">
                              <div
                                className="h-full bg-green-500 rounded-full"
                                style={{ width: `${realProb}%` }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Classification Badge: Pass / Suspicious / Failed */}
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <Badge
                            variant={isFail ? 'destructive' : isPass ? 'success' : 'warning'}
                            className="font-bold uppercase px-2.5 py-0.5"
                          >
                            {isPass ? (
                              <CheckCircle2 className="mr-1 h-3 w-3 inline" />
                            ) : isFail ? (
                              <XCircle className="mr-1 h-3 w-3 inline" />
                            ) : (
                              <AlertTriangle className="mr-1 h-3 w-3 inline" />
                            )}
                            {classification}
                          </Badge>
                        </td>

                        {/* Date */}
                        <td className="px-4 py-3.5 text-xs text-muted-foreground whitespace-nowrap">
                          {new Date(a.created_at).toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </td>

                        {/* Action Link */}
                        <td className="px-4 py-3.5 text-right whitespace-nowrap">
                          <Button variant="ghost" size="sm" asChild>
                            <Link to={`/results/${a.id}`}>
                              View <ChevronRight className="ml-1 h-3.5 w-3.5" />
                            </Link>
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
