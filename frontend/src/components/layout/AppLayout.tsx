import { Outlet } from 'react-router-dom'

import { Footer } from '@/components/layout/Footer'
import { Header } from '@/components/layout/Header'
import { ScrollToTop } from '@/components/layout/ScrollToTop'

export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <ScrollToTop />
      {/* Skip link: the first tab stop on every page. */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 focus:rounded-lg focus:bg-clay-500 focus:px-4 focus:py-2 focus:text-white"
      >
        تخطَّ إلى المحتوى
      </a>
      <Header />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
