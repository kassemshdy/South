import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useSeo } from '@/hooks/useSeo'

export function NotFoundPage() {
  useSeo({ title: 'الصفحة غير موجودة | دليل الجنوب', noIndex: true })

  return (
    <div className="container-page flex flex-col items-center justify-center py-24 text-center">
      <p className="text-6xl font-bold text-clay-300">404</p>
      <h1 className="mt-4 text-2xl">الصفحة غير موجودة</h1>
      <p className="mt-2 max-w-md text-ink-500">
        قد يكون الرابط قديماً أو أن النشاط لم يعد منشوراً.
      </p>
      <div className="mt-8 flex gap-3">
        <Button asChild>
          <Link to="/">الصفحة الرئيسية</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/businesses">دليل الأعمال</Link>
        </Button>
      </div>
    </div>
  )
}
