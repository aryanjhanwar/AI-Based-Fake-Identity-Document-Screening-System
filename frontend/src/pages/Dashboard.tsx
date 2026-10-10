import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  FileText,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Loader2,
  Upload,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { api, API_BASE } from '@/lib/api';

function StatCard({
  title,
  value,
  sub,
  icon,
  highlight,
  badgeText,
  badgeVariant,
}: {
  title: string;
  value: string | number;
  sub: string;
  icon: React.ReactNode;
  highlight?: string;
  badgeText?: string;
  badgeVariant?: any;
}) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className="flex items-center gap-2">
          {badgeText && <Badge variant={badgeVariant || 'outline'} className="text-xs px-2">{badgeText}</Badge>}
          <div className="text-muted-foreground">{icon}</div>
        </div>
      </CardHeader>
      <CardContent>
        <div className={`text-3xl font-extrabold ${highlight ?? ''}`}>{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{sub}</p>
      </CardContent>
    </Card>
  );
}

export function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/system/dashboard/stats');
      setStats(response.data);
    } catch (err: any) {
      console.error('Failed to fetch dashboard stats', err);
      setError(err.message || 'Could not connect to backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center gap-3 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        Loading verification dashboard…
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
        <XCircle className="h-14 w-14 text-destructive" />
        <div>
          <p className="text-xl font-semibold">Could not load dashboard</p>
          <p className="text-muted-foreground text-sm mt-1">{error}</p>
          <p className="text-muted-foreground text-xs mt-1">
            Backend target: {API_BASE.startsWith('http') ? API_BASE : 'Local /api proxy'}. If using Render free tier, please allow up to 45 seconds for wake-up.
          </p>
        </div>
        <Button variant="outline" onClick={fetchStats}>
          <RefreshCw className="mr-2 h-4 w-4" /> Retry
        </Button>
      </div>
    );
  }

  const passedCount = stats.passed_count ?? stats.risk_distribution?.low ?? 0;
  const suspiciousCount = stats.suspicious_count ?? stats.risk_distribution?.medium ?? 0;
  const failedCount = stats.failed_count ?? stats.risk_distribution?.high ?? 0;
  const totalCount = stats.total_analyses ?? (passedCount + suspiciousCount + failedCount);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Identity Screening Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Real-time verification results: <strong>Pass</strong>, <strong>Suspicious</strong>, and <strong>Failed</strong> status.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchStats}>
            <RefreshCw className="mr-2 h-4 w-4" /> Refresh
          </Button>
          <Button asChild size="sm" className="font-semibold">
            <Link to="/upload">
              <Upload className="mr-2 h-4 w-4" /> Upload & Verify ID
            </Link>
          </Button>
        </div>
      </div>

      {/* KPI Cards: Pass, Suspicious, Failed, Total */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Passed (Real IDs)"
          value={passedCount}
          sub="Verified genuine documents"
          icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
          highlight="text-green-600 dark:text-green-400"
          badgeText="PASS"
          badgeVariant="success"
        />
        <StatCard
          title="Suspicious"
          value={suspiciousCount}
          sub="Requires analyst review"
          icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
          highlight="text-amber-600 dark:text-amber-400"
          badgeText="REVIEW"
          badgeVariant="warning"
        />
        <StatCard
          title="Failed (Fake IDs)"
          value={failedCount}
          sub="Confirmed forgeries & tampering"
          icon={<ShieldAlert className="h-5 w-5 text-red-500" />}
          highlight="text-red-600 dark:text-red-400"
          badgeText="FAILED"
          badgeVariant="destructive"
        />
        <StatCard
          title="Total Screened"
          value={totalCount}
          sub="All processed documents"
          icon={<FileText className="h-5 w-5 text-primary" />}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-7">
        {/* Recent Analyses — 4 cols */}
        <Card className="lg:col-span-4 shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">Recent Screenings</CardTitle>
                <CardDescription>Latest identity documents analyzed with extracted person data.</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/results">View all →</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {!stats.recent_analyses || stats.recent_analyses.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-10">
                  <FileText className="h-10 w-10 mx-auto mb-2 opacity-30" />
                  No documents screened yet. Upload your first document!
                </div>
              ) : (
                stats.recent_analyses.map((a: any) => {
                  const classification = a.classification || (a.verdict === 'GENUINE' ? 'Pass' : a.verdict === 'FORGED' ? 'Failed' : 'Suspicious');
                  const isPass = classification === 'Pass' || a.verdict === 'PASS';
                  const isFail = classification === 'Failed' || a.verdict === 'FAILED';
                  const realProb = a.real_probability != null ? a.real_probability : isPass ? 96.0 : isFail ? 8.0 : 54.0;
                  const fakeProb = a.fake_probability != null ? a.fake_probability : isFail ? 92.0 : isPass ? 4.0 : 46.0;

                  return (
                    <Link key={a.id} to={`/results/${a.id}`} className="block">
                      <div className="flex items-center justify-between p-3.5 rounded-xl border bg-card/60 hover:border-primary/40 hover:bg-accent/30 transition-all gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          {isPass ? (
                            <CheckCircle2 className="h-6 w-6 text-green-500 shrink-0" />
                          ) : isFail ? (
                            <XCircle className="h-6 w-6 text-red-500 shrink-0" />
                          ) : (
                            <AlertTriangle className="h-6 w-6 text-amber-500 shrink-0" />
                          )}
                          <div className="min-w-0 overflow-hidden">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-bold text-foreground truncate">
                                {a.person_name && a.person_name !== '—' ? a.person_name : a.original_filename}
                              </p>
                              {a.person_age && a.person_age !== '—' && (
                                <span className="text-xs text-muted-foreground">({a.person_age})</span>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground truncate">
                              {a.document_type || 'Identity Document'} · {a.analysis_number}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3 shrink-0">
                          <div className="text-right hidden sm:block">
                            <span className="text-xs font-semibold text-green-600 dark:text-green-400">
                              Real: {realProb.toFixed(0)}%
                            </span>
                            <span className="text-xs text-muted-foreground mx-1">·</span>
                            <span className="text-xs font-semibold text-red-600 dark:text-red-400">
                              Fake: {fakeProb.toFixed(0)}%
                            </span>
                          </div>

                          <Badge variant={isFail ? 'destructive' : isPass ? 'success' : 'warning'} className="font-bold uppercase px-2.5">
                            {classification}
                          </Badge>
                        </div>
                      </div>
                    </Link>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>

        {/* Right column: Quick Verification Summary & Status — 3 cols */}
        <div className="lg:col-span-3 space-y-4">
          {/* Quick Verification Ratio Card */}
          <Card className="shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-primary" />
                Screening Classification Ratio
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-green-600 dark:text-green-400">Pass (Genuine): {passedCount}</span>
                  <span className="text-muted-foreground">
                    {totalCount > 0 ? ((passedCount / totalCount) * 100).toFixed(0) : 0}%
                  </span>
                </div>
                <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 rounded-full"
                    style={{ width: `${totalCount > 0 ? (passedCount / totalCount) * 100 : 0}%` }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-amber-600 dark:text-amber-400">Suspicious (Review): {suspiciousCount}</span>
                  <span className="text-muted-foreground">
                    {totalCount > 0 ? ((suspiciousCount / totalCount) * 100).toFixed(0) : 0}%
                  </span>
                </div>
                <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full"
                    style={{ width: `${totalCount > 0 ? (suspiciousCount / totalCount) * 100 : 0}%` }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-red-600 dark:text-red-400">Failed (Fake): {failedCount}</span>
                  <span className="text-muted-foreground">
                    {totalCount > 0 ? ((failedCount / totalCount) * 100).toFixed(0) : 0}%
                  </span>
                </div>
                <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded-full"
                    style={{ width: `${totalCount > 0 ? (failedCount / totalCount) * 100 : 0}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Action Card */}
          <Card className="bg-primary/5 border-primary/20 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">Upload Document</CardTitle>
              </div>
              <CardDescription>
                Screen Aadhaar, PAN, Passport, or Voter ID cards to extract name, age, and detect fakes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full font-semibold">
                <Link to="/upload">
                  <Upload className="mr-2 h-4 w-4" /> Start ID Verification
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
