import { Link } from 'react-router-dom'
import { Store } from 'lucide-react'

export function Footer() {
  return (
    <footer className="mt-20 border-t border-ink-100 bg-white">
      <div className="container-page grid gap-8 py-12 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <div className="flex items-center gap-2.5 font-display text-lg font-bold">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-clay-500 text-white">
              <Store className="h-5 w-5" aria-hidden="true" />
            </span>
            دليل الجنوب
          </div>
          <p className="mt-3 max-w-sm leading-relaxed text-ink-500">
            اكتشف وادعم الأعمال المحلية في جنوب لبنان — من المطاعم والمحال إلى الحرف والخدمات.
          </p>
        </div>

        <nav aria-label="روابط سريعة">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">روابط سريعة</h2>
          <ul className="space-y-2 text-ink-500">
            <li><Link to="/businesses" className="hover:text-clay-600">دليل الأعمال</Link></li>
            <li><Link to="/dashboard/businesses/new" className="hover:text-clay-600">أضف نشاطك التجاري</Link></li>
            <li><Link to="/login" className="hover:text-clay-600">تسجيل الدخول</Link></li>
          </ul>
        </nav>

        <div>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-700">عن المنصة</h2>
          <p className="leading-relaxed text-ink-500">
            كل نشاط يُنشر بعد مراجعته من فريق الإدارة، لضمان دليل موثوق لأهل الجنوب.
          </p>
        </div>
      </div>

      <div className="border-t border-ink-100 py-5 text-center text-sm text-ink-500">
        © {new Date().getFullYear()} دليل الجنوب — صُنع لدعم المجتمع المحلي.
      </div>
    </footer>
  )
}
