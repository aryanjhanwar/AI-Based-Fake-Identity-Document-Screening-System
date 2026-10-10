import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  UploadCloud,
  FileText,
  X,
  ShieldCheck,
  CheckCircle2,
  Image as ImageIcon,
  Zap,
  Brain,
  Fingerprint,
  ScanLine,
  Sparkles,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { api, API_BASE } from '@/lib/api';

const DOC_TYPES = [
  { value: 'unknown',          label: 'Auto-Detect (AI)' },
  { value: 'aadhaar',          label: 'Aadhaar Card' },
  { value: 'pan',              label: 'PAN Card' },
  { value: 'driving_license',  label: 'Driving License' },
  { value: 'passport',         label: 'Passport' },
  { value: 'voter_id',         label: 'Voter ID' },
];

const PIPELINE_STEPS = [
  { icon: <Brain className="h-4 w-4" />,        label: 'OCR Cardholder Detection (Name, Age, DOB)' },
  { icon: <ScanLine className="h-4 w-4" />,     label: 'Document Type & Layout Verification' },
  { icon: <Fingerprint className="h-4 w-4" />,  label: 'Anti-Tampering & Splicing Check' },
  { icon: <Zap className="h-4 w-4" />,          label: 'Official Seal & Emblem Forensics' },
  { icon: <ImageIcon className="h-4 w-4" />,    label: 'Photo & Portrait Authenticity Check' },
  { icon: <ShieldCheck className="h-4 w-4" />,  label: 'Real / Fake Probability Scoring' },
];

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [docType, setDocType] = useState('unknown');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [samples, setSamples] = useState<any[]>([]);
  const [loadingSampleId, setLoadingSampleId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Load available sample documents from backend
  useEffect(() => {
    api.get('/samples')
      .then((res) => {
        if (res.data?.samples) {
          setSamples(res.data.samples);
        }
      })
      .catch(() => {});
  }, []);

  const acceptFile = (f: File) => {
    if (!f.type.startsWith('image/')) {
      setError('Please upload an image file (JPEG, PNG, WEBP).');
      return;
    }
    if (f.size > 15 * 1024 * 1024) {
      setError('File exceeds 15 MB limit.');
      return;
    }
    setFile(f);
    setError(null);
    const reader = new FileReader();
    reader.onloadend = () => setPreviewUrl(reader.result as string);
    reader.readAsDataURL(f);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) acceptFile(selected);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) acceptFile(dropped);
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    if (docType !== 'unknown') {
      formData.append('document_type', docType);
    }

    try {
      const response = await api.post('/analysis/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      // Navigate to the result page immediately
      navigate(`/results/${response.data.id}`);
    } catch (err: any) {
      console.error(err);
      const targetDesc = API_BASE.startsWith('http') ? API_BASE : 'the backend';
      let msg = `Upload failed. Could not reach ${targetDesc}.`;
      if (err.response?.data?.detail) {
        msg = err.response.data.detail;
      } else if (err.response?.data?.error) {
        msg = err.response.data.error;
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        msg = 'Analysis request timed out. If Render is waking up from sleep, wait 30 seconds and try again.';
      } else if (err.message?.toLowerCase().includes('network error')) {
        msg = `Network Error: Could not connect to backend (${targetDesc}). If on Render free tier, the service may be waking up from sleep (~45s), or VITE_API_URL is missing in Netlify.`;
      } else if (err.message) {
        msg = `${err.message} (${targetDesc})`;
      }
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleLoadSample = async (sample: any) => {
    setLoadingSampleId(sample.id);
    setError(null);
    try {
      const res = await api.get(`/samples/${sample.id}/file`, { responseType: 'blob' });
      const sampleBlob = res.data;
      const sampleFile = new File([sampleBlob], sample.filename || `${sample.id}.jpg`, {
        type: 'image/jpeg',
      });
      setDocType(sample.type || 'aadhaar');
      acceptFile(sampleFile);
    } catch (err) {
      setError('Could not load sample file from server.');
    } finally {
      setLoadingSampleId(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analyze Document</h1>
        <p className="text-muted-foreground mt-1">
          Upload an identity document to screen whether it is <strong>Original</strong>, <strong>Fake</strong>, or <strong>Suspicious</strong>.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Upload Card */}
        <div className="md:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Document Upload & Scan</CardTitle>
              <CardDescription>Supports JPG, PNG, WEBP · Max 15 MB</CardDescription>
            </CardHeader>
            <CardContent>
              {!file ? (
                <div
                  className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer flex flex-col items-center justify-center min-h-[280px] transition-all ${
                    isDragging
                      ? 'border-primary bg-primary/5 scale-[1.01]'
                      : 'border-border hover:border-primary/50 hover:bg-accent/30'
                  }`}
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <UploadCloud
                    className={`h-14 w-14 mb-3 transition-colors ${
                      isDragging ? 'text-primary' : 'text-muted-foreground'
                    }`}
                  />
                  <h3 className="text-lg font-semibold mb-1">
                    {isDragging ? 'Drop document to screen' : 'Click or drag document here'}
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Aadhaar Card, PAN Card, Passport, Voter ID, or Driving License
                  </p>
                  <Button variant="secondary" type="button">Select Image File</Button>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleFileSelect}
                  />
                </div>
              ) : (
                <div className="rounded-xl border bg-card overflow-hidden">
                  <div className="relative bg-black/10 flex items-center justify-center p-4 min-h-[300px]">
                    <img
                      src={previewUrl!}
                      alt="Uploaded preview"
                      className="max-h-[380px] object-contain rounded-md shadow-md"
                    />
                    <Button
                      variant="destructive"
                      size="icon"
                      className="absolute top-3 right-3 h-8 w-8 rounded-full"
                      onClick={() => {
                        setFile(null);
                        setPreviewUrl(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="p-4 border-t flex items-center bg-muted/20 gap-3">
                    <FileText className="h-5 w-5 text-primary shrink-0" />
                    <div className="flex-1 overflow-hidden">
                      <p className="text-sm font-medium truncate">{file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(file.size / 1024 / 1024).toFixed(2)} MB · {file.type}
                      </p>
                    </div>
                    <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-md text-sm flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </CardContent>
            <CardFooter className="justify-between border-t pt-4 gap-4 flex-wrap">
              <p className="text-xs text-muted-foreground">
                Document is analyzed locally using offline AI weights.
              </p>
              <Button
                size="lg"
                onClick={handleUpload}
                disabled={!file || isUploading}
                className="w-full sm:w-auto font-semibold px-6"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Scanning Document & Extracting OCR Details...
                  </>
                ) : (
                  <>
                    <ShieldCheck className="mr-2 h-5 w-5" />
                    Analyze Document
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>

          {/* Quick Test Samples */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">1-Click Test With Real Dataset Samples</CardTitle>
              </div>
              <CardDescription>
                Test the screening pipeline instantly using genuine and forged samples from the dataset.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid sm:grid-cols-2 gap-3">
                {samples.map((s) => {
                  const isExpectedFake = s.expected === 'FORGED';
                  const isLoadingThis = loadingSampleId === s.id;
                  return (
                    <div
                      key={s.id}
                      className="p-3 rounded-lg border bg-card hover:border-primary/50 transition-all flex flex-col justify-between gap-3"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-sm">{s.title}</span>
                          <Badge variant={isExpectedFake ? 'destructive' : 'success'}>
                            {s.expected}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">{s.description}</p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isLoadingThis || isUploading}
                        onClick={() => handleLoadSample(s)}
                        className="w-full"
                      >
                        {isLoadingThis ? (
                          <>
                            <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Loading...
                          </>
                        ) : (
                          'Load Document'
                        )}
                      </Button>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Options & Pipeline Sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Document Configuration</CardTitle>
              <CardDescription>Target document category</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Document Type</label>
                <select
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                >
                  {DOC_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  Select or leave Auto-Detect to let the AI determine the type.
                </p>
              </div>

              <div className="border-t pt-4 space-y-3">
                <h4 className="text-sm font-semibold">Verification Pipeline</h4>
                <ul className="space-y-2.5">
                  {PIPELINE_STEPS.map((step, i) => (
                    <li key={i} className="flex items-center gap-2.5 text-xs text-muted-foreground">
                      <span className="text-primary shrink-0">{step.icon}</span>
                      {step.label}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="border-t pt-4">
                <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-primary">⚡ Instant ID Verification</p>
                  <p>Accurate screening for Aadhaar, PAN, Voter ID, Passport, and DL.</p>
                  <p>Detects cardholder details via OCR and evaluates Real vs Fake probability for Pass, Suspicious, or Failed verdict.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
