import { useEffect, useState } from "react";
import apiClient from "../api/client";

export default function Dashboard() {
  const [company, setCompany] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

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

    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return <p className="text-slate-500">Loading company data…</p>;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        Failed to load company data: {error}
      </div>
    );
  }

  if (!company) {
    return (
      <p className="text-slate-500">
        No company profile found. Run <code>python manage.py seed_brain</code> on
        the backend.
      </p>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-navy">Dashboard</h1>
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
    </div>
  );
}