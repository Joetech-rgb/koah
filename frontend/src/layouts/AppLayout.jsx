import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/leads", label: "Leads" },
  { to: "/drafts", label: "Drafts" },
  { to: "/draft-tester", label: "Draft Tester" },
  { to: "/settings", label: "Settings" },
];

export default function AppLayout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 bg-navy text-white flex flex-col">
        <div className="px-6 py-5 text-xl font-semibold tracking-tight">
          KoahCloud
        </div>
        <nav className="flex flex-col gap-1 px-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-teal text-navy"
                    : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 bg-slate-50 p-8">
        <Outlet />
      </main>
    </div>
  );
}
