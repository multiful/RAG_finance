/**
 * 개인정보처리방침 - Google AdSense 및 이용자 보호 요건 충족
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield } from 'lucide-react';

export default function PrivacyPolicyPage() {
  return (
    <div className="max-w-3xl mx-auto py-8 px-4 animate-page-enter">
      <Card className="border-none shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <Shield className="w-6 h-6 text-indigo-600" />
            개인정보처리방침
          </CardTitle>
          <p className="text-sm text-slate-500">
            최종 업데이트: 2025년 2월 · RegTech PRO 서비스
          </p>
        </CardHeader>
        <CardContent className="prose prose-slate max-w-none text-sm space-y-6">
          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">1. 개요</h2>
            <p className="text-slate-600 leading-relaxed">
              RegTech PRO(이하 서비스)는 스테이블코인·STO 결합 환경의 규제·리스크 Gap 분석을 지원하며, 금융 규제·정책 정보 수집·분석 및 AI 기반 질의응답을 제공하는 플랫폼입니다.
              이용자의 개인정보를 소중히 하며, 개인정보 보호법 및 관련 법령을 준수합니다.
            </p>
          </section>
          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">2. 수집하는 개인정보 항목 및 이용 목적</h2>
            <ul className="list-disc pl-5 text-slate-600 space-y-1">
              <li>서비스 이용 시: 이메일 주소(로그인·계정 관리), 접속 로그(IP, 접속 시각, 브라우저 정보)는 서비스 운영·보안·통계에만 이용됩니다.</li>
              <li>AI 질의: 질문·답변 내용은 서비스 품질 개선 및 검색·답변 생성에 이용될 수 있으며, 개인을 식별할 수 있는 정보와 결합해 저장하지 않습니다.</li>
              <li>선택 정보: 알림 구독·설정 시 입력한 이메일은 해당 기능 제공 및 법적 고지에만 사용됩니다.</li>
            </ul>
          </section>
          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">3. 보유·이용 기간</h2>
            <p className="text-slate-600 leading-relaxed">
              수집된 개인정보는 목적 달성 후 지체 없이 파기하거나, 법령에서 정한 보존 기간이 있는 경우 해당 기간 동안만 보관합니다.
            </p>
          </section>
          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">4. 제3자 제공 및 위탁</h2>
            <p className="text-slate-600 leading-relaxed">
              이용자의 개인정보를 원칙적으로 제3자에게 제공하지 않습니다. 법령에 따른 요청 또는 이용자 동의가 있는 경우,
              또는 서비스 제공을 위해 필요한 범위 내에서 위탁(호스팅, 분석 도구 등)할 수 있으며, 위탁 시 수탁자 및 목적을 안내합니다.
            </p>
          </section>
          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">5. 쿠키 및 유사 기술</h2>
            <p className="text-slate-600 leading-relaxed">
              서비스는 세션 유지·설정 저장·접속 통계를 위해 쿠키 및 로컬 스토리지를 사용할 수 있습니다.
              제3자 광고 서비스(예: Google AdSense)를 사용하는 경우 해당 제공자의 쿠키 정책이 적용될 수 있으며,
              이용자는 브라우저 설정을 통해 쿠키 사용을 제한할 수 있습니다.
            </p>
          </section>
          <section>
            <h2 className="text-base font-semibold text-slate-900 mt-6 mb-2">6. 이용자 권리 및 문의</h2>
            <p className="text-slate-600 leading-relaxed">
              이용자는 개인정보의 열람·정정·삭제·처리정지를 요청할 수 있으며, 요청 시 지체 없이 법령에 따라 조치하고 결과를 통지합니다.
              변경된 정책은 웹사이트에 게시한 날로부터 효력이 발생합니다.
            </p>
          </section>
          <p className="text-slate-500 text-xs mt-8 pt-4 border-t border-slate-100">
            본 방침은 서비스의 개인정보 처리 방식을 설명하며, 법령 및 정책 변경에 따라 수정될 수 있습니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
