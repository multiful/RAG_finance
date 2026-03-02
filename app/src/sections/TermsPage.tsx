/**
 * 이용약관 및 면책조항 - Google AdSense·금융 서비스 요건 충족
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText } from 'lucide-react';
import { SOURCE_LABEL_FULL } from '@/lib/constants';

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto py-8 px-4 animate-page-enter">
      <Card className="border-none shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <FileText className="w-6 h-6 text-indigo-600" />
            이용약관 및 면책조항
          </CardTitle>
          <p className="text-sm text-slate-500">
            최종 업데이트: 2025년 2월 · RegTech PRO 서비스
          </p>
        </CardHeader>
        <CardContent className="prose prose-slate max-w-none text-sm space-y-6">
          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">제1조 (목적)</h2>
            <p className="text-slate-600 leading-relaxed">
              본 약관은 RegTech PRO(이하 &quot;서비스&quot;)의 이용 조건 및 절차, 이용자와 운영자 간 권리·의무 및 책임 사항,
              기타 필요한 사항을 규정함을 목적으로 합니다.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">제2조 (서비스의 성격)</h2>
            <p className="text-slate-600 leading-relaxed">
              본 서비스는 {SOURCE_LABEL_FULL} 등 공개된 규제·정책 정보를 수집·정리하여 대시보드·트렌드·키워드 분석 및
              AI 기반 질의응답 형태로 제공하는 정보 플랫폼입니다. 원문은 해당 기관 공식 채널에서 확인하시기 바랍니다.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">제3조 (면책조항 · 중요)</h2>
            <ul className="list-disc pl-5 text-slate-600 space-y-2">
              <li>
                <strong>투자·금융 조언 아님:</strong> 본 서비스의 모든 콘텐츠·분석·AI 답변은 정보 제공 목적이며,
                투자 권유, 금융 상품 판매·추천, 법률·회계·세무 자문이 아닙니다. 투자·영업 결정은 이용자 본인의 판단과 책임 하에 이루어져야 합니다.
              </li>
              <li>
                <strong>정확성:</strong> 수집·가공 과정에서 지연·오류·생략이 있을 수 있으며, 법적 효력·시행일·해석은
                반드시 공식 공표문·관할 기관의 안내를 기준으로 확인하시기 바랍니다.
              </li>
              <li>
                <strong>손해:</strong> 서비스 이용으로 인한 직·간접 손해에 대해 운영자는 법령에서 정하는 범위를 넘어
                책임지지 않습니다.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">제4조 (이용 규칙)</h2>
            <p className="text-slate-600 leading-relaxed">
              이용자는 서비스를 법령 및 본 약관에 따라 이용하여야 하며, 타인의 정보를 도용하거나 서비스 운영을 방해하는
              행위, 저작권·개인정보 등 제3자 권리를 침해하는 행위를 해서는 안 됩니다. 위반 시 서비스 이용 제한 및
              법적 조치가 있을 수 있습니다.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">제5조 (저작권 및 데이터)</h2>
            <p className="text-slate-600 leading-relaxed">
              서비스에 게시된 공공 정보의 저작권은 해당 기관에 있으며, 서비스의 구조·디자인·분석 결과물 등은
              운영자에게 귀속됩니다. 상업적 무단 전재·배포는 금지됩니다.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">제6조 (약관 변경)</h2>
            <p className="text-slate-600 leading-relaxed">
              본 약관은 필요한 경우 변경될 수 있으며, 변경 시 서비스 내 공지 또는 별도 안내합니다.
              변경 후에도 이용을 계속하시면 변경 약관에 동의한 것으로 봅니다.
            </p>
          </section>

          <p className="text-slate-500 text-xs mt-8 pt-4 border-t border-slate-100">
            서비스 이용과 관련한 문의는 개인정보처리방침에 안내된 연락처를 이용해 주시기 바랍니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
