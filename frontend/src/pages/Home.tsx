import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            FastAPI + React Template
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Vite + React + TypeScript + Tailwind CSS + React Router + TanStack Query
          </p>
          <div className="flex justify-center gap-4">
            <Link
              to="/about"
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              About
            </Link>
            <a
              href="/api/system/healthcheck"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
            >
              API Health Check
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
