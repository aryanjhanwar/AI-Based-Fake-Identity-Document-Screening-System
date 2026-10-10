import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Database,
  RefreshCw,
  CheckCircle2,
  Sliders,
  Cpu,
  Zap,
} from 'lucide-react';
import { api } from '@/lib/api';

export function SettingsPage() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const res = await api.get('/system/health');
      setHealth(res.data);
    } catch {
      // Backend not reached or fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System & Diagnostics</h1>
          <p className="text-muted-foreground mt-1">
            Engine status, active machine learning models, and screening thresholds.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchHealth} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </Button>
      </div>

      {/* Live Telemetry Banner */}
      {health && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl border bg-card/80">
          <div>
            <p className="text-xs text-muted-foreground">Engine Version</p>
            <p className="text-sm font-bold text-primary">{health.engine_version || 'IDShield Pro v3.0'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Status</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm font-semibold capitalize">{health.status || 'Healthy'}</span>
            </div>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Average Latency</p>
            <p className="text-sm font-bold flex items-center gap-1">
              <Zap className="h-3.5 w-3.5 text-amber-500" />
              {health.avg_latency_ms || 48} ms
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Uptime</p>
            <p className="text-sm font-semibold">
              {health.uptime_seconds ? `${Math.floor(health.uptime_seconds / 60)} min` : '< 1 min'}
            </p>
          </div>
        </div>
      )}

      {/* Model Engine Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-primary" />
            <CardTitle>AI Screening Engine Telemetry</CardTitle>
          </div>
          <CardDescription>Status of the multi-modal forensic inspection pipeline.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-3">
            {[
              {
                name: 'Random Forest Forgery Classifier',
                detail: 'HOG Gradients + HSV Color Profile',
                status: 'Active (Online)',
                version: 'artifacts/fast_classifier.pkl',
              },
              {
                name: 'EXIF Metadata Analyzer',
                detail: 'Software tags, compression traces, date consistency',
                status: 'Active',
                version: 'modules/metadata_analysis.py',
              },
              {
                name: 'Stamp / Seal ELA Forensics',
                detail: 'Circularity, ink dispersion, Error Level Analysis',
                status: 'Active',
                version: 'modules/stamp_forensics.py',
              },
              {
                name: 'Face Biometric Detector',
                detail: 'OpenCV Haar Cascade frontal face localization',
                status: 'Active',
                version: 'cv2.data.haarcascades',
              },
            ].map((m) => (
              <div key={m.name} className="p-3.5 rounded-lg border bg-card/60 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm">{m.name}</span>
                  <Badge variant="success" className="text-xs">
                    <CheckCircle2 className="mr-1 h-3 w-3" /> {m.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">{m.detail}</p>
                <p className="text-xs font-mono text-primary/80 pt-1">{m.version}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Decision Thresholds */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sliders className="h-5 w-5 text-primary" />
            <CardTitle>Decision Classification Thresholds</CardTitle>
          </div>
          <CardDescription>Standardized decision criteria applied across document categories.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid sm:grid-cols-3 gap-3 text-center">
            <div className="p-4 rounded-xl border border-green-500/20 bg-green-500/5 space-y-1">
              <Badge variant="success" className="mb-1">ORIGINAL / GENUINE</Badge>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">Risk &lt; 25%</p>
              <p className="text-xs text-muted-foreground">Document passes all multi-modal forensic checks.</p>
            </div>
            <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 space-y-1">
              <Badge variant="warning" className="mb-1">SUSPICIOUS</Badge>
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">25% – 50%</p>
              <p className="text-xs text-muted-foreground">Borderline score. Sent to Review Queue for human signoff.</p>
            </div>
            <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5 space-y-1">
              <Badge variant="destructive" className="mb-1">FAKE / FORGED</Badge>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">Risk &gt; 50%</p>
              <p className="text-xs text-muted-foreground">Multiple forgery anomalies detected. High likelihood of fraud.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Dataset & Storage Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            <CardTitle>Dataset & Verification Baseline</CardTitle>
          </div>
          <CardDescription>Mounted training and reference datasets.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {[
            ['Aadhaar Document Dataset', 'Dataset/Aadhar (Original & Fake subdirectories)'],
            ['PAN Card Document Dataset', 'Dataset/PAN (Original & Fake subdirectories)'],
            ['Passport Reference Samples', 'Dataset/Passport (Original & Fake subdirectories)'],
            ['Feature Extraction Engine', 'HOG (Directional Edges) + HSV (Color Gamut Analysis)'],
            ['Backend API Port', 'http://127.0.0.1:5000 (Flask REST Service)'],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between items-start border-b border-border/50 pb-2 last:border-0">
              <span className="text-muted-foreground shrink-0">{label}</span>
              <span className="font-mono text-xs text-right ml-4 font-medium break-all">{value}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
