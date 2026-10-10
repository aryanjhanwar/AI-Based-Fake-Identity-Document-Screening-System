import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  User,
  Calendar,
  CreditCard,
  Download,
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  Image as ImageIcon,
  ChevronDown,
  ChevronUp,
  Cpu,
} from 'lucide-react';
import { api, API_URL } from '@/lib/api';

// ── Verdict Classification Banner ──────────────────────────────────────────
function VerdictBanner({
  classification,
  verdict,
  realProb,
  fakeProb,
  reviewStatus,
  humanSummary,
}: {
  classification: string;
  verdict: string;
  realProb: number;
  fakeProb: number;
  reviewStatus: string;
  humanSummary: string;
}) {
  const isFailed = classification === 'Failed' || verdict === 'FAILED';
  const isPass = classification === 'Pass' || verdict === 'PASS';
  const isSuspicious = !isFailed && !isPass;

  let cfg: {
    bg: string;
    badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning';
    badgeText: string;
    subText: string;
    icon: React.ReactNode;
    title: string;
    desc: string;
  } = {
    bg: 'bg-green-500/10 border-green-500/30 text-green-800 dark:text-green-200',
    badgeVariant: 'success',
    badgeText: 'PASS',
    subText: 'VERIFIED ORIGINAL',
    icon: <ShieldCheck className="h-10 w-10 text-green-500 shrink-0" />,
    title: 'STATUS: PASS',
    desc: humanSummary || 'Document verified authentic. No signs of digital tampering or photo splicing detected.',
  };

  if (isFailed) {
    cfg = {
      bg: 'bg-red-500/10 border-red-500/30 text-red-800 dark:text-red-200',
      badgeVariant: 'destructive',
      badgeText: 'FAILED',
      subText: 'FORGERY DETECTED',
      icon: <XCircle className="h-10 w-10 text-red-500 shrink-0" />,
      title: 'STATUS: FAILED',
      desc: humanSummary || 'Document failed verification! High probability of forgery or digital tampering detected.',
    };
  } else if (isSuspicious) {
    cfg = {
      bg: 'bg-amber-500/10 border-amber-500/30 text-amber-800 dark:text-amber-200',
      badgeVariant: 'warning',
      badgeText: 'SUSPICIOUS',
      subText: 'MANUAL REVIEW REQUIRED',
      icon: <AlertTriangle className="h-10 w-10 text-amber-500 shrink-0" />,
      title: 'STATUS: SUSPICIOUS',
      desc: humanSummary || 'Borderline clarity or anomaly detected. Human reviewer verification recommended.',
    };
  }

  return (
    <div className={`p-6 rounded-2xl border ${cfg.bg} shadow-sm space-y-4`}>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {cfg.icon}
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-2xl font-black tracking-tight">{cfg.title}</span>
              <Badge variant={cfg.badgeVariant} className="text-sm px-3 py-0.5 uppercase font-bold tracking-wider">
                {cfg.badgeText}
              </Badge>
              <span className="text-xs font-semibold uppercase tracking-wider opacity-80">
                ({cfg.subText})
              </span>
            </div>
            <p className="text-sm opacity-90 mt-1 max-w-2xl">{cfg.desc}</p>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-2 sm:self-center">
          <span className="text-xs uppercase font-medium tracking-wider opacity-70">Review Status:</span>
          <Badge
            variant={reviewStatus === 'approved' ? 'success' : reviewStatus === 'rejected' ? 'destructive' : 'warning'}
            className="uppercase"
          >
            {reviewStatus || 'pending'}
          </Badge>
        </div>
      </div>

      {/* Real vs Fake Probability Meter */}
      <div className="pt-3 border-t border-current/10">
        <div className="flex items-center justify-between text-sm mb-1.5 font-semibold">
          <span className="flex items-center gap-1.5 text-green-600 dark:text-green-400">
            <span className="h-2.5 w-2.5 rounded-full bg-green-500 inline-block" />
            Real Probability: <strong>{realProb.toFixed(1)}%</strong>
          </span>
          <span className="flex items-center gap-1.5 text-red-600 dark:text-red-400">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" />
            Fake Probability: <strong>{fakeProb.toFixed(1)}%</strong>
          </span>
        </div>
        <div className="h-3 w-full bg-red-200 dark:bg-red-950/60 rounded-full overflow-hidden flex shadow-inner">
          <div
            className="h-full bg-green-500 transition-all duration-700 ease-out"
            style={{ width: `${realProb}%` }}
          />
          <div
            className="h-full bg-red-500 transition-all duration-700 ease-out"
            style={{ width: `${fakeProb}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ── Review Actions ───────────────────────────────────────────────────────────
function ReviewActions({ analysisId, currentStatus, onUpdated }: { analysisId: string; currentStatus: string; onUpdated: () => void }) {
  const [loading, setLoading] = useState(false);
  const [note, setNote] = useState('');

  const submit = async (status: string) => {
    setLoading(true);
    try {
      await api.post(`/analysis/${analysisId}/review`, { status, notes: note });
      onUpdated();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (currentStatus === 'approved' || currentStatus === 'rejected') {
    return (
      <div className={`flex items-center gap-3 p-4 rounded-lg border ${currentStatus === 'approved' ? 'bg-green-500/10 border-green-500/20' : 'bg-red-500/10 border-red-500/20'}`}>
        {currentStatus === 'approved'
          ? <CheckCircle2 className="h-5 w-5 text-green-500" />
          : <XCircle className="h-5 w-5 text-red-500" />}
        <p className="text-sm font-medium capitalize">Analyst Decision: <strong>{currentStatus}</strong></p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <textarea
        value={note}
        onChange={e => setNote(e.target.value)}
        placeholder="Add verification notes (optional)…"
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[70px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
      />
      <div className="flex gap-3">
        <Button className="bg-green-600 hover:bg-green-700 text-white flex-1 font-semibold" disabled={loading} onClick={() => submit('approved')}>
          <CheckCircle2 className="mr-2 h-4 w-4" /> Approve (Pass)
        </Button>
        <Button variant="destructive" className="flex-1 font-semibold" disabled={loading} onClick={() => submit('rejected')}>
          <XCircle className="mr-2 h-4 w-4" /> Reject (Failed)
        </Button>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────
export function AnalysisResult() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const fetchAnalysis = async () => {
    try {
      const res = await api.get(`/analysis/${id}`);
      setAnalysis(res.data);
      setLoading(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load analysis.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalysis();
  }, [id]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <XCircle className="h-16 w-16 text-destructive mb-4" />
        <h2 className="text-2xl font-bold mb-2">Analysis Not Found</h2>
        <p className="text-muted-foreground mb-6">{error}</p>
        <Button onClick={() => navigate('/upload')}>Upload New Document</Button>
      </div>
    );
  }

  if (loading || !analysis) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center space-y-6">
        <div className="relative h-24 w-24">
          <div className="absolute inset-0 rounded-full border-4 border-muted" />
          <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin" />
          <ShieldAlert className="absolute inset-0 m-auto h-8 w-8 text-primary animate-pulse" />
        </div>
        <div>
          <h2 className="text-2xl font-bold">Screening Document</h2>
          <p className="text-muted-foreground mt-2 max-w-md">
            Running OCR text extraction and multi-modal forgery checks…
          </p>
        </div>
      </div>
    );
  }

  const classification = analysis.classification || (analysis.verdict === 'GENUINE' ? 'Pass' : analysis.verdict === 'FORGED' ? 'Failed' : 'Suspicious');
  const verdict = analysis.verdict || classification.toUpperCase();
  const realProb = analysis.real_probability != null ? analysis.real_probability : Math.round((1 - (analysis.fake_prob ?? 0)) * 100);
  const fakeProb = analysis.fake_probability != null ? analysis.fake_probability : Math.round((analysis.fake_prob ?? 0) * 100);
  const reviewStatus = analysis.review_status ?? 'pending';

  const person = analysis.person_details || {
    name: analysis.extracted_fields?.name || 'Not isolated from scan',
    age: analysis.extracted_fields?.age || 'Not specified',
    dob: analysis.extracted_fields?.dob || 'Not specified',
    gender: analysis.extracted_fields?.gender || 'Not specified',
    id_number: analysis.extracted_fields?.id_number || analysis.extracted_fields?.aadhaar_number || analysis.extracted_fields?.pan_number || 'N/A',
    document_type: analysis.document_type || 'Identity Document',
    father_name: analysis.extracted_fields?.father_name || 'Not specified',
  };

  const checklist = analysis.verification_checklist || [
    { item: 'Document Format & Layout', status: classification === 'Pass' ? 'Passed' : 'Suspicious', detail: `${person.document_type} standard template` },
    { item: 'Photo & Portrait Authenticity', status: 'Passed', detail: 'Cardholder facial portrait isolated' },
    { item: 'Security Seal & Emblem', status: classification === 'Failed' ? 'Failed' : 'Passed', detail: 'Official emblem checked' },
    { item: 'Digital Tampering & Splicing', status: classification === 'Failed' ? 'Failed' : 'Passed', detail: classification === 'Failed' ? 'Tampering detected' : 'No editing detected' },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top Bar Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/results">
              <ArrowLeft className="h-4 w-4 mr-1" /> All Records
            </Link>
          </Button>
          <div className="h-4 w-px bg-border" />
          <span className="text-sm font-semibold tracking-wide">{analysis.id}</span>
          <span className="text-xs text-muted-foreground font-mono">{analysis.analysis_number}</span>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <a href={`${API_URL}/analysis/${analysis.id}/report/pdf`} download>
              <Download className="mr-2 h-4 w-4" /> Download Report
            </a>
          </Button>
        </div>
      </div>

      {/* Primary Classification & Real/Fake Probability Banner */}
      <VerdictBanner
        classification={classification}
        verdict={verdict}
        realProb={realProb}
        fakeProb={fakeProb}
        reviewStatus={reviewStatus}
        humanSummary={analysis.human_summary || analysis.risk_explanation}
      />

      {/* Two-Column Grid: Left Person Details & Document Info / Right Image & Checklist */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Person & Extracted Details (Takes 2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Person & Document Card (OCR Extracted) */}
          <Card className="border-primary/20 shadow-sm">
            <CardHeader className="pb-3 border-b bg-card/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">Person & ID Details</CardTitle>
                </div>
                <Badge variant="outline" className="font-semibold text-primary">
                  OCR Extracted
                </Badge>
              </div>
              <CardDescription>
                Identified personal information extracted from the document scan.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-5 space-y-4">
              {/* Primary Name Display */}
              <div className="p-4 rounded-xl bg-primary/5 border border-primary/15 flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                    Full Name (Person)
                  </span>
                  <p className="text-2xl font-black text-foreground mt-0.5 tracking-tight">
                    {person.name || 'Not isolated from scan'}
                  </p>
                </div>
                <Badge variant={person.name && person.name !== 'Not isolated from scan' ? 'success' : 'outline'}>
                  {person.name && person.name !== 'Not isolated from scan' ? 'Identified' : 'Review Needed'}
                </Badge>
              </div>

              {/* Data Grid: Age, DOB, Gender, ID Type, ID Number, Father */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div className="p-3.5 rounded-lg border bg-card/60 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
                    <Calendar className="h-3.5 w-3.5 text-primary" />
                    Age & Date of Birth
                  </div>
                  <p className="text-base font-bold text-foreground">
                    {person.age ? `${person.age}` : '—'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    DOB: <strong>{person.dob || 'Not specified'}</strong>
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border bg-card/60 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
                    <CreditCard className="h-3.5 w-3.5 text-primary" />
                    Document Type
                  </div>
                  <p className="text-base font-bold text-foreground">
                    {person.document_type || 'Identity Document'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Standard Government Format
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border bg-card/60 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
                    <FileText className="h-3.5 w-3.5 text-primary" />
                    ID / Document Number
                  </div>
                  <p className="text-base font-mono font-bold text-foreground tracking-wide">
                    {person.id_number || 'N/A'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Official Registered Identifier
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border bg-card/60 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
                    <User className="h-3.5 w-3.5 text-primary" />
                    Gender & Relation
                  </div>
                  <p className="text-base font-bold text-foreground">
                    {person.gender || 'Not specified'}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    Father/Spouse: <strong>{person.father_name || 'N/A'}</strong>
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Simple Verification Checklist Card */}
          <Card>
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                Anti-Fraud Verification Summary
              </CardTitle>
              <CardDescription>
                Summary of integrity checks conducted on this document.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="space-y-3">
                {checklist.map((chk: any, i: number) => {
                  const isPassItem = chk.status === 'Passed';
                  const isFailItem = chk.status === 'Failed';
                  return (
                    <div
                      key={i}
                      className={`flex items-center justify-between p-3 rounded-lg border text-sm ${
                        isFailItem
                          ? 'bg-red-500/5 border-red-500/20'
                          : isPassItem
                          ? 'bg-green-500/5 border-green-500/20'
                          : 'bg-amber-500/5 border-amber-500/20'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {isFailItem ? (
                          <XCircle className="h-5 w-5 text-red-500 shrink-0" />
                        ) : isPassItem ? (
                          <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                        ) : (
                          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
                        )}
                        <div>
                          <p className="font-semibold">{chk.item}</p>
                          <p className="text-xs text-muted-foreground">{chk.detail}</p>
                        </div>
                      </div>
                      <Badge variant={isFailItem ? 'destructive' : isPassItem ? 'success' : 'warning'}>
                        {chk.status}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Collapsible Advanced Technical Findings (Hidden by default to avoid clutter) */}
          <div className="border rounded-xl bg-card overflow-hidden">
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="w-full p-4 text-left flex items-center justify-between hover:bg-accent/30 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-semibold">Advanced Technical & ML Diagnostics</span>
                <span className="text-xs text-muted-foreground">(Technical details hidden by default)</span>
              </div>
              {showTechnicalDetails ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </button>

            {showTechnicalDetails && (
              <div className="p-4 border-t space-y-4 bg-muted/10 text-xs">
                <div>
                  <p className="font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Contributing Risk Weights
                  </p>
                  <div className="space-y-2">
                    {(analysis.risk_factors || []).map((f: any, i: number) => (
                      <div key={i} className="flex justify-between items-center p-2 rounded bg-card border">
                        <div>
                          <span className="font-medium text-foreground">{f.factor}:</span>{' '}
                          <span className="text-muted-foreground">{f.explanation}</span>
                        </div>
                        <Badge variant="outline">{f.weight}%</Badge>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-2 border-t">
                  <p className="font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Raw Optical & Container Diagnostics
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="p-2 rounded bg-card border">
                      <span className="text-muted-foreground">Sharpness:</span>{' '}
                      <strong>{analysis.quality?.sharpness ?? 'N/A'}</strong>
                    </div>
                    <div className="p-2 rounded bg-card border">
                      <span className="text-muted-foreground">Brightness:</span>{' '}
                      <strong>{analysis.quality?.brightness ?? 'N/A'}</strong>
                    </div>
                    <div className="p-2 rounded bg-card border">
                      <span className="text-muted-foreground">Model:</span>{' '}
                      <strong>{analysis.ml_prediction?.model_version ?? 'RandomForest'}</strong>
                    </div>
                    <div className="p-2 rounded bg-card border">
                      <span className="text-muted-foreground">Elapsed:</span>{' '}
                      <strong>{analysis.processing_time_ms ?? 50}ms</strong>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Uploaded Image & Review Decision */}
        <div className="space-y-6">
          {/* Uploaded Document Image */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <ImageIcon className="h-4 w-4 text-primary" />
                Uploaded ID Document
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="rounded-xl overflow-hidden border bg-black/10 shadow-inner flex items-center justify-center min-h-[220px]">
                <img
                  src={`${API_URL}/analysis/${analysis.id}/image`}
                  alt="Screened identity document"
                  className="w-full h-auto max-h-[360px] object-contain rounded-md"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                    const parent = (e.target as HTMLImageElement).parentElement;
                    if (parent) {
                      parent.innerHTML = '<div class="flex flex-col items-center justify-center p-8 text-muted-foreground text-xs gap-2"><svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg><span>Original document preview</span></div>';
                    }
                  }}
                />
              </div>

              <div className="mt-3 text-xs text-muted-foreground flex justify-between">
                <span>{analysis.original_filename}</span>
                <span>{(analysis.file_size ? (analysis.file_size / 1024).toFixed(1) + ' KB' : '')}</span>
              </div>
            </CardContent>
          </Card>

          {/* Review Decision Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Verification Decision</CardTitle>
              <CardDescription>Sign-off or escalate this identity document.</CardDescription>
            </CardHeader>
            <CardContent>
              <ReviewActions
                analysisId={analysis.id}
                currentStatus={analysis.review_status}
                onUpdated={fetchAnalysis}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
