import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, FileImage, FolderUp, Loader2, ShieldCheck, XCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';

type Classification = 'Pass' | 'Suspicious' | 'Failed';

type DatasetResult = {
  file: File;
  id?: string;
  classification?: Classification;
  humanSummary?: string;
  error?: string;
};

const MAX_FILES = 50;
const MAX_FILE_SIZE = 15 * 1024 * 1024;

function getErrorMessage(error: unknown) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string; error?: string } } }).response;
    return response?.data?.detail || response?.data?.error;
  }
  if (error instanceof Error) return error.message;
  return undefined;
}

export function DatasetUploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [results, setResults] = useState<DatasetResult[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentFile, setCurrentFile] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectFiles = (selectedFiles: FileList | null) => {
    if (!selectedFiles) return;

    const selected = Array.from(selectedFiles);
    const invalidType = selected.find((file) => !file.type.startsWith('image/'));
    if (invalidType) {
      setError(`${invalidType.name} is not an image. Upload JPG, PNG, or WEBP documents only.`);
      return;
    }
    const oversized = selected.find((file) => file.size > MAX_FILE_SIZE);
    if (oversized) {
      setError(`${oversized.name} exceeds the 15 MB per-file limit.`);
      return;
    }
    if (selected.length > MAX_FILES) {
      setError(`Select up to ${MAX_FILES} documents per verification batch.`);
      return;
    }

    setFiles(selected);
    setResults([]);
    setError(null);
  };

  const processDataset = async () => {
    if (!files.length || isProcessing) return;

    setIsProcessing(true);
    setCurrentFile(0);
    setResults([]);
    setError(null);

    const processed: DatasetResult[] = [];
    for (const [index, file] of files.entries()) {
      setCurrentFile(index + 1);
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await api.post('/analysis/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        const analysis = response.data;
        processed.push({
          file,
          id: analysis.id,
          classification: analysis.classification,
          humanSummary: analysis.human_summary,
        });
      } catch (uploadError) {
        processed.push({
          file,
          error: getErrorMessage(uploadError) || 'Verification failed for this document.',
        });
      }
      setResults([...processed]);
    }

    setIsProcessing(false);
  };

  const clearDataset = () => {
    setFiles([]);
    setResults([]);
    setCurrentFile(0);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const completed = results.filter((result) => result.classification).length;
  const failed = results.filter((result) => result.classification === 'Failed' || result.error).length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload Dataset</h1>
        <p className="text-muted-foreground mt-1">
          Institutes and organisations can upload multiple student or employee documents and verify every record in one batch.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderUp className="h-5 w-5 text-primary" />
            Batch document verification
          </CardTitle>
          <CardDescription>
            Each image is checked for document authenticity, tampering, OCR consistency, and portrait anomalies. A failed check is flagged as a possible intruder or forged document.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div
            className="rounded-xl border-2 border-dashed border-border p-8 text-center hover:border-primary/50 hover:bg-accent/20 transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <FileImage className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
            <p className="font-semibold">Select student or employee documents</p>
            <p className="text-sm text-muted-foreground mt-1">JPG, PNG, or WEBP · up to {MAX_FILES} files · 15 MB each</p>
            <Button type="button" variant="secondary" className="mt-4">
              Choose Documents
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(event) => selectFiles(event.target.files)}
            />
          </div>

          {files.length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/20 p-4">
              <div>
                <p className="font-semibold">{files.length} document{files.length === 1 ? '' : 's'} selected</p>
                <p className="text-xs text-muted-foreground">
                  {isProcessing ? `Verifying ${currentFile} of ${files.length}...` : 'Ready for verification'}
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={clearDataset} disabled={isProcessing}>Clear</Button>
                <Button onClick={processDataset} disabled={isProcessing}>
                  {isProcessing ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Verifying...</>
                  ) : (
                    <><ShieldCheck className="mr-2 h-4 w-4" /> Verify Dataset</>
                  )}
                </Button>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-md text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {results.length > 0 && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="font-semibold">Verification results</h2>
                  <p className="text-sm text-muted-foreground">{completed} of {files.length} documents processed</p>
                </div>
                {failed > 0 && (
                  <Badge variant="destructive">
                    <XCircle className="mr-1 h-3.5 w-3.5" /> {failed} failed / intruder flag{failed === 1 ? '' : 's'}
                  </Badge>
                )}
              </div>
              <div className="divide-y rounded-lg border">
                {results.map((result) => {
                  const isFailed = result.classification === 'Failed' || result.error;
                  const isSuspicious = result.classification === 'Suspicious';
                  return (
                    <div key={`${result.file.name}-${result.file.lastModified}`} className="flex flex-wrap items-center gap-3 p-3">
                      {isFailed ? (
                        <XCircle className="h-5 w-5 text-destructive shrink-0" />
                      ) : isSuspicious ? (
                        <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
                      ) : (
                        <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="font-medium truncate">{result.file.name}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {result.error || result.humanSummary || 'Document passed verification checks.'}
                        </p>
                      </div>
                      <Badge variant={isFailed ? 'destructive' : isSuspicious ? 'warning' : 'success'}>
                        {result.error ? 'FAILED' : result.classification?.toUpperCase()}
                      </Badge>
                      {result.id && (
                        <Button asChild variant="outline" size="sm">
                          <Link to={`/results/${result.id}`}>View details</Link>
                        </Button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
