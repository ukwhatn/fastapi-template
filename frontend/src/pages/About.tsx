import { Link } from 'react-router-dom'

export default function About() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white rounded-lg shadow-md p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">About This Template</h1>

          <div className="prose max-w-none">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Backend</h2>
            <ul className="list-disc list-inside text-gray-600 mb-6 space-y-2">
              <li>FastAPI 0.120.0+ with Python 3.13+</li>
              <li>Clean Architecture (4-layer)</li>
              <li>SQLAlchemy 2.0+ with PostgreSQL</li>
              <li>RDB-based encrypted session management</li>
              <li>Docker Compose multi-profile setup</li>
            </ul>

            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Frontend</h2>
            <ul className="list-disc list-inside text-gray-600 mb-6 space-y-2">
              <li>Vite 6.x for fast development</li>
              <li>React 18.x with TypeScript 5.x</li>
              <li>React Router 6.x for routing</li>
              <li>TanStack Query for data fetching</li>
              <li>Tailwind CSS 4.x for styling</li>
            </ul>

            <div className="mt-8">
              <Link
                to="/"
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition inline-block"
              >
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
