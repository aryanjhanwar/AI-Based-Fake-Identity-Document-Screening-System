import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3, TrendingUp, ShieldAlert, Users } from 'lucide-react';

export function Analytics() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics & Reports</h1>
        <p className="text-muted-foreground mt-2">
          System-wide performance, fraud detection trends, and model accuracy metrics.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">14,231</div>
            <p className="text-xs text-muted-foreground">+20.1% from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Fraud Detected</CardTitle>
            <ShieldAlert className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">842</div>
            <p className="text-xs text-muted-foreground">+4.3% from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Avg Process Time</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.2s</div>
            <p className="text-xs text-muted-foreground">-0.1s from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Model Accuracy</CardTitle>
            <BarChart3 className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">98.5%</div>
            <p className="text-xs text-muted-foreground">+0.2% from last month</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Fraud by Document Type</CardTitle>
            <CardDescription>
              Distribution of detected forgeries across different document formats.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center">
                <div className="w-full flex-1">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">PAN Card</span>
                    <span className="text-sm font-medium">45%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: '45%' }} />
                  </div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-full flex-1">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">Aadhaar Card</span>
                    <span className="text-sm font-medium">35%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: '35%' }} />
                  </div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-full flex-1">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">Passport</span>
                    <span className="text-sm font-medium">15%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: '15%' }} />
                  </div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-full flex-1">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">Driving License</span>
                    <span className="text-sm font-medium">5%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: '5%' }} />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Fraud Indicators Triggered</CardTitle>
            <CardDescription>
              The most common forensic anomalies found in rejected documents.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { label: 'Copy-Move Forgery (ELA)', value: 320 },
                { label: 'Missing Security Features', value: 245 },
                { label: 'Font Inconsistencies', value: 180 },
                { label: 'Metadata Tampering', value: 97 },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between p-3 rounded-lg border bg-card/50">
                  <span className="text-sm font-medium">{item.label}</span>
                  <span className="text-sm text-muted-foreground font-mono">{item.value} cases</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
