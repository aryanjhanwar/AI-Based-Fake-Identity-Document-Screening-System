import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronRight,
  Loader2,
  ClipboardCheck,
  RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api';

export function ReviewQueue() {
  const [items, setItems]     = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState<'pending' | 'resolved'>('pending');

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await api.get('/analysis', {
        params: { status: 'review_required', limit: 50 },
      });
      setItems(res.data.items ?? []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch(); }, []);

  const pending  = items.filter(i => !i.review_status || i.review_status === 'pending');
  const resolved = items.filter(i => i.review_status && i.review_status !== 'pending');
  const displayed = tab === 'pending' ? pending : resolved;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Review Queue</h1>
          <p className="text-muted-foreground mt-1">
            {pending.length} document{pending.length !== 1 ? 's' : ''} awaiting human verification
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetch}>
          <RefreshCw className="mr-2 h-4 w-4" /> Refresh
        </Button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Pending Review', value: pending.length,  color: 'text-yellow-400', icon: <AlertTriangle className="h-5 w-5 text-yellow-400" /> },
          { label: 'Approved',       value: resolved.filter(r => r.review_status === 'approved').length,  color: 'text-green-400', icon: <CheckCircle2 className="h-5 w-5 text-green-400" /> },
          { label: 'Rejected',       value: resolved.filter(r => r.review_status === 'rejected').length,  color: 'text-red-400',   icon: <XCircle className="h-5 w-5 text-red-400" /> },
        ].map(s => (
          <Card key={s.label}>
            <CardContent className="pt-4 flex items-center gap-3">
              {s.icon}
              <div>
                <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-muted-foreground">{s.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border rounded-lg p-1 bg-muted/30 w-fit">
        {(['pending', 'resolved'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all capitalize ${
              tab === t ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t} ({t === 'pending' ? pending.length : resolved.length})
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : displayed.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-20 text-center text-muted-foreground">
            <ClipboardCheck className="h-12 w-12 mb-3 opacity-30" />
            <p className="font-medium">{tab === 'pending' ? 'No items pending review' : 'No resolved items'}</p>
            <p className="text-sm mt-1">
              {tab === 'pending'
                ? 'All flagged documents have been reviewed.'
                : 'No documents have been approved or rejected yet.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {displayed.map((item) => {
            const isHigh = item.risk_level === 'high' || item.risk_level === 'critical';
            return (
              <Card
                key={item.id}
                className={`border transition-colors ${isHigh ? 'border-red-500/30' : 'border-yellow-500/30'}`}
              >
                <CardContent className="flex items-center gap-4 pt-4 pb-4">
                  {/* Risk indicator */}
                  <div className={`h-10 w-1 rounded-full shrink-0 ${isHigh ? 'bg-red-500' : 'bg-yellow-500'}`} />

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-sm">{item.analysis_number}</p>
                      <Badge variant={isHigh ? 'destructive' : 'warning'} className="text-xs">
                        {item.risk_level?.toUpperCase()}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {(item.document_type ?? 'unknown').toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 truncate">{item.original_filename}</p>
                    <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                      <Clock className="h-3 w-3" />
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                    {item.risk_explanation && (
                      <p className="text-xs text-muted-foreground mt-2 line-clamp-2 italic border-l-2 border-border pl-2">
                        {item.risk_explanation}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col sm:flex-row items-end sm:items-center gap-2 shrink-0">
                    {tab === 'pending' && (
                      <>
                        <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white w-full sm:w-auto">
                          <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" /> Approve
                        </Button>
                        <Button size="sm" variant="destructive" className="w-full sm:w-auto">
                          <XCircle className="mr-1.5 h-3.5 w-3.5" /> Reject
                        </Button>
                      </>
                    )}
                    {tab === 'resolved' && (
                      <Badge variant={item.review_status === 'approved' ? 'success' : 'destructive'} className="text-sm px-3 py-1">
                        {item.review_status?.toUpperCase()}
                      </Badge>
                    )}
                    <Button variant="ghost" size="sm" asChild>
                      <Link to={`/results/${item.id}`}>
                        Details <ChevronRight className="ml-1 h-3 w-3" />
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
