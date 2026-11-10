import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import apiClient from "../api/client";

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-navy">{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const [company, setCompany] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const [businessesToday, setBusinessesToday] = useState(0);
  const [sentToday, setSentToday] = useState(0);
  const [repliesToday, setRepliesToday] = useState(0);
  const [digests, setDigests] = useState([]);

  useEffect(() => {
    let isMounted = true;
    const today = new Date().toISOString().slice(0, 10);

    apiClient
      .get("brain/company/")
      .then((response) => {
        if (!isMounted) return;
        const first = Array.isArray(response.data)
          ? response.data[0]
          : response.data.results?.[0];
        setCompany(first ?? null);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    apiClient
      .get("crm/companies/")
      .then((res) => {
        if (!isMounted) return;
        const list = res.data.results ?? res.data;
        const todayCount = list.filter((c) => c.created_at?.startsWith(today)).length;
        setBusinessesToday(todayCount);
      })
      .catch(() => {});

    apiClient
      .get(`outreach/messages/?date=${today}`)
      .then((res) => {
        if (!isMounted) return;
        const list = res.data.results ?? res.data;
        setSentToday(list.filter((m) => m.direction === "outbound").length);
        setRepliesToday(list.filter((m) => m.direction === "inbound").length);
      })
      .catch(() => {});

    apiClient
      .get("reporting/digests/")
      .then((res) => {
        if (!isMounted) return;
        setDigests(res.data.results ?? res.data);
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-navy">Dashboard</h1>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Businesses found today" value={businessesToday} />
        <StatCard label="Emails sent today" value={sentToday} />
        <StatCard label="Replies received today" value={repliesToday} />
      </div>

      {loading && <p className="mt-6 text-slate-500">Loading company data...</p>}
      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          Failed to load company data: {error}
        </div>
      )}
      {!loading && !error && company && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-medium text-navy">{company.name}</h2>
          <p className="mt-2 text-slate-600">{company.description}</p>
          <div className="mt-4 flex gap-6 text-sm text-slate-500">
            <span>
              <strong className="text-slate-700">Based in:</strong> {company.based_in}
            </span>
            <span>
              <strong className="text-slate-700">Tone:</strong> {company.email_tone}
            </span>
          </div>
        </div>
      )}
      {!loading && !error && !company && (
        <p className="mt-6 text-slate-500">
          No company profile found. Run <code>python manage.py seed_brain</code> on the backend.
        </p>
      )}

      <div className="mt-8">
        <h2 className="text-xl font-semibold text-navy mb-3">Recent Reports</h2>
        {digests.length === 0 ? (
          <p className="text-slate-400">No daily digests yet.</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {digests.map((d) => (
              <Link
                key={d.id}
                to={`/reports/${d.date}`}
                className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
              >
                <p className="font-medium text-navy">{d.date}</p>
                <p className="text-sm text-slate-500 mt-1">
                  {d.businesses_found} found &middot; {d.emails_sent} sent &middot; {d.replies_received} replies
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
