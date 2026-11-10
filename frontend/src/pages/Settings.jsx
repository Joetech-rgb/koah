import { useEffect, useState } from "react";
import apiClient from "../api/client";

export default function Settings() {
  const [niches, setNiches] = useState([]);
  const [newNiche, setNewNiche] = useState("");
  const [newRegion, setNewRegion] = useState("");
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  const loadNiches = () => {
    apiClient
      .get("prospecting/niches/")
      .then((res) => setNiches(res.data.results ?? res.data))
      .catch((err) => setError(err.message));
  };

  useEffect(() => {
    loadNiches();
    apiClient
      .get("reporting/digests/stats/")
      .then((res) => setStats(res.data))
      .catch(() => {});
  }, []);

  const addNiche = async (e) => {
    e.preventDefault();
    if (!newNiche || !newRegion) return;
    try {
      await apiClient.post("prospecting/niches/", {
        niche_name: newNiche,
        region: newRegion,
        active: true,
      });
      setNewNiche("");
      setNewRegion("");
      loadNiches();
    } catch (err) {
      setError(err.message);
    }
  };

  const toggleActive = async (niche) => {
    try {
      await apiClient.patch(`prospecting/niches/${niche.id}/`, {
        active: !niche.active,
      });
      loadNiches();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-navy">Settings</h1>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      <div className="mt-6">
        <h2 className="text-xl font-semibold text-navy mb-3">Target Niches</h2>

        <form onSubmit={addNiche} className="flex gap-3 mb-4">
          <input
            type="text"
            placeholder="Niche name"
            value={newNiche}
            onChange={(e) => setNewNiche(e.target.value)}
            className="border rounded px-3 py-2 flex-1 focus:outline-none focus:ring-2 focus:ring-teal"
          />
          <input
            type="text"
            placeholder="Region"
            value={newRegion}
            onChange={(e) => setNewRegion(e.target.value)}
            className="border rounded px-3 py-2 flex-1 focus:outline-none focus:ring-2 focus:ring-teal"
          />
          <button
            type="submit"
            className="bg-teal text-navy px-4 py-2 rounded font-medium hover:opacity-90"
          >
            Add Niche
          </button>
        </form>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-navy text-white">
              <tr>
                <th className="text-left px-4 py-3">Niche</th>
                <th className="text-left px-4 py-3">Region</th>
                <th className="text-left px-4 py-3">Active</th>
              </tr>
            </thead>
            <tbody>
              {niches.map((n) => (
                <tr key={n.id} className="border-t">
                  <td className="px-4 py-3">{n.niche_name}</td>
                  <td className="px-4 py-3">{n.region}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleActive(n)}
                      className={`px-3 py-1 rounded text-xs font-medium ${
                        n.active ? "bg-green-100 text-green-800" : "bg-gray-200 text-gray-600"
                      }`}
                    >
                      {n.active ? "Active" : "Inactive"}
                    </button>
                  </td>
                </tr>
              ))}
              {niches.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-gray-400">
                    No niches configured yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold text-navy mb-3">System Health</h2>
        {stats ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-sm text-slate-500">AI cost this month</p>
              <p className="mt-1 text-2xl font-semibold text-navy">${stats.cost_this_month.toFixed(2)}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-sm text-slate-500">Sent this week vs last</p>
              <p className="mt-1 text-2xl font-semibold text-navy">
                {stats.emails_sent_this_week} / {stats.emails_sent_last_week}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-sm text-slate-500">Reply rate (7d)</p>
              <p className="mt-1 text-2xl font-semibold text-navy">
                {(stats.reply_rate_7d * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        ) : (
          <p className="text-slate-400">Loading stats...</p>
        )}
      </div>
    </div>
  );
}
