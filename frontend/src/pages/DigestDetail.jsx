import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import apiClient from "../api/client";

export default function DigestDetail() {
  const { date } = useParams();
  const [digest, setDigest] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    apiClient
      .get(`reporting/digests/${date}/`)
      .then((res) => {
        if (isMounted) setDigest(res.data);
      })
      .catch((err) => {
        if (isMounted) setError(err.message);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [date]);

  if (loading) return <p className="text-slate-500">Loading...</p>;
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        Failed to load digest: {error}
      </div>
    );
  }
  if (!digest) return <p className="text-slate-500">No digest found for {date}.</p>;

  return (
    <div>
      <Link to="/" className="text-sm text-teal hover:underline">
        &larr; Back to Dashboard
      </Link>
      <h1 className="text-2xl font-semibold text-navy mt-2">Report for {digest.date}</h1>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Businesses found</p>
          <p className="mt-1 text-2xl font-semibold text-navy">{digest.businesses_found}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Emails sent</p>
          <p className="mt-1 text-2xl font-semibold text-navy">{digest.emails_sent}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Replies received</p>
          <p className="mt-1 text-2xl font-semibold text-navy">{digest.replies_received}</p>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold text-navy mb-3">Hot Leads</h2>
        {digest.hot_leads.length === 0 ? (
          <p className="text-slate-400">No hot leads for this day.</p>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm divide-y">
            {digest.hot_leads.map((lead, idx) => (
              <div key={idx} className="p-4">
                <p className="font-medium text-navy">{lead.name}</p>
                <p className="text-sm text-slate-500">{lead.reason}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
