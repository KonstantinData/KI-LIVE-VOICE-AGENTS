/** Haupt-Layout mit Sidebar und Header. */

import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { removeToken } from '../lib/auth';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/leads', label: 'Leads', icon: '👥' },
  { to: '/conversations', label: 'Gespräche', icon: '💬' },
  { to: '/costs', label: 'Kosten', icon: '€' },
  { to: '/appointments', label: 'Termine', icon: '📅' },
  { to: '/followups', label: 'Follow-ups', icon: '🔔' },
  { to: '/knowledge', label: 'Wissensbasis', icon: '📚' },
  { to: '/feedback', label: 'Feedback', icon: '⭐' },
  { to: '/settings', label: 'Einstellungen', icon: '⚙️' },
];

export function Layout() {
  const navigate = useNavigate();

  const handleLogout = () => {
    removeToken();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-lg font-bold text-gray-900">KI-Team</h1>
          <p className="text-xs text-gray-500 mt-1">Dashboard</p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-600 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-200">
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Abmelden
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
