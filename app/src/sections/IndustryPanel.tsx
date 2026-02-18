import { useEffect, useState } from 'react';
import { 
  Building2, 
  Landmark, 
  TrendingUp, 
  FileText, 
  Search,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getDocuments, classifyIndustry } from '@/lib/api';
import type { Document, IndustryClassification } from '@/types';

interface DocumentWithClassification extends Document {
  classification?: IndustryClassification;
  classifying?: boolean;
}

export default function IndustryPanel() {
  const [documents, setDocuments] = useState<DocumentWithClassification[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedIndustry, setSelectedIndustry] = useState<string>('all');

  const fetchDocuments = async () => {
    try {
      const data = await getDocuments({ page_size: 50, days: 30 });
      setDocuments(data.documents);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleClassify = async (doc: DocumentWithClassification) => {
    setDocuments(prev => 
      prev.map(d => 
        d.document_id === doc.document_id 
          ? { ...d, classifying: true } 
          : d
      )
    );

    try {
      const result = await classifyIndustry({ document_id: doc.document_id });
      setDocuments(prev => 
        prev.map(d => 
          d.document_id === doc.document_id 
            ? { ...d, classification: result, classifying: false } 
            : d
        )
      );
    } catch (error) {
      console.error('Error classifying:', error);
      setDocuments(prev => 
        prev.map(d => 
          d.document_id === doc.document_id 
            ? { ...d, classifying: false } 
            : d
        )
      );
    }
  };

  const getIndustryIcon = (industry: string) => {
    switch (industry) {
      case 'INSURANCE':
        return <Building2 className="w-5 h-5" />;
      case 'BANKING':
        return <Landmark className="w-5 h-5" />;
      case 'SECURITIES':
        return <TrendingUp className="w-5 h-5" />;
      default:
        return null;
    }
  };

  const getIndustryLabel = (industry: string) => {
    switch (industry) {
      case 'INSURANCE':
        return '보험';
      case 'BANKING':
        return '은행';
      case 'SECURITIES':
        return '증권';
      default:
        return industry;
    }
  };

  const getIndustryColor = (industry: string) => {
    switch (industry) {
      case 'INSURANCE':
        return 'bg-sky-100 text-sky-700 border-sky-200';
      case 'BANKING':
        return 'bg-violet-100 text-violet-700 border-violet-200';
      case 'SECURITIES':
        return 'bg-pink-100 text-pink-700 border-pink-200';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = doc.title.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (selectedIndustry === 'all') return matchesSearch;
    
    const hasClassification = doc.classification?.predicted_labels?.includes(selectedIndustry);
    return matchesSearch && hasClassification;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="section-title">업권 영향 분류</h2>
        <p className="text-muted-foreground mt-1">
          문서별 보험/은행/증권 업권 영향도 자동 분류
        </p>
      </div>

      {/* Industry Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="card-elevated border-l-4 border-l-sky-400">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-sky-100 flex items-center justify-center">
                <Building2 className="w-6 h-6 text-sky-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">보험 영향</p>
                <p className="text-2xl font-bold">
                  {documents.filter(d => 
                    d.classification?.predicted_labels?.includes('INSURANCE')
                  ).length}건
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-elevated border-l-4 border-l-violet-400">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-violet-100 flex items-center justify-center">
                <Landmark className="w-6 h-6 text-violet-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">은행 영향</p>
                <p className="text-2xl font-bold">
                  {documents.filter(d => 
                    d.classification?.predicted_labels?.includes('BANKING')
                  ).length}건
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-elevated border-l-4 border-l-pink-400">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-pink-100 flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-pink-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">증권 영향</p>
                <p className="text-2xl font-bold">
                  {documents.filter(d => 
                    d.classification?.predicted_labels?.includes('SECURITIES')
                  ).length}건
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter & Search */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="문서 제목 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Tabs value={selectedIndustry} onValueChange={setSelectedIndustry}>
          <TabsList>
            <TabsTrigger value="all">전체</TabsTrigger>
            <TabsTrigger value="INSURANCE">보험</TabsTrigger>
            <TabsTrigger value="BANKING">은행</TabsTrigger>
            <TabsTrigger value="SECURITIES">증권</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Document List */}
      <Card className="card-elevated">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            문서 목록 ({filteredDocuments.length}건)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredDocuments.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                검색 결과가 없습니다
              </p>
            ) : (
              filteredDocuments.map((doc) => (
                <div 
                  key={doc.document_id}
                  className="p-4 bg-muted/50 rounded-xl"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="font-medium">{doc.title}</p>
                      <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                        <span>{new Date(doc.published_at).toLocaleDateString('ko-KR')}</span>
                        <span>{doc.category}</span>
                      </div>
                    </div>
                    
                    {!doc.classification ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleClassify(doc)}
                        disabled={doc.classifying}
                      >
                        {doc.classifying ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          '분류하기'
                        )}
                      </Button>
                    ) : (
                      <div className="flex items-center gap-2">
                        {doc.classification.predicted_labels.map((label) => (
                          <Badge 
                            key={label}
                            className={`${getIndustryColor(label)}`}
                          >
                            {getIndustryIcon(label)}
                            <span className="ml-1">{getIndustryLabel(label)}</span>
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Classification Details */}
                  {doc.classification && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                            <Building2 className="w-4 h-4" />
                            보험
                          </div>
                          <Progress 
                            value={doc.classification.label_insurance * 100} 
                            className="h-2"
                          />
                          <p className="text-xs text-right mt-1">
                            {(doc.classification.label_insurance * 100).toFixed(0)}%
                          </p>
                        </div>
                        <div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                            <Landmark className="w-4 h-4" />
                            은행
                          </div>
                          <Progress 
                            value={doc.classification.label_banking * 100} 
                            className="h-2"
                          />
                          <p className="text-xs text-right mt-1">
                            {(doc.classification.label_banking * 100).toFixed(0)}%
                          </p>
                        </div>
                        <div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                            <TrendingUp className="w-4 h-4" />
                            증권
                          </div>
                          <Progress 
                            value={doc.classification.label_securities * 100} 
                            className="h-2"
                          />
                          <p className="text-xs text-right mt-1">
                            {(doc.classification.label_securities * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                      
                      {doc.classification.explanation && (
                        <div className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
                          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                          <p>{doc.classification.explanation}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
