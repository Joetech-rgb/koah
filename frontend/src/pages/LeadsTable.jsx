import { useEffect, useState } from "react";
import client from "../api/client";

const STATUS_STYLES = {
  new: "bg-gray-200 text-gray-800",
  researched: "bg-blue-100 text-blue-800",
  drafted: "bg-purple-100 text-purple-800",
  sent: "bg-teal-100 text-teal-800",
  replied: "bg-green-100 text-green-800",
  closed: "bg-slate-300 text-slate-800",
};

export default function LeadsTable() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    client
      .get("crm/companies/")
      .then((res) => setCompanies(res.data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = companies.filter((c) => {
    const matchesSearch = c.name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter ? c.status === statusFilter : true;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-[#10193A] mb-4">Leads</h1>

      <div className="flex gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border rounded px-3 py-2 flex-1 focus:outline-none focus:ring-2 focus:ring-[#3FB8AA]"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#3FB8AA]"
        >
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="researched">Researched</option>
          <option value="drafted">Drafted</option>
          <option value="sent">Sent</option>
          <option value="replied">Replied</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {loading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-600">{error}</p>}

      {!loading && !error && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#10193A] text-white">
              <tr>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Domain</th>
                <th className="text-left px-4 py-3">Country</th>
                <th className="text-left px-4 py-3">Industry</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Contact Email</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} className="border-t">
                  <td className="px-4 py-3">{c.name}</td>
                  <td className="px-4 py-3">{c.domain || "-"}</td>
                  <td className="px-4 py-3">{c.country || "-"}</td>
                  <td className="px-4 py-3">{c.industry || "-"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_STYLES[c.status] || ""}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">{c.contact_email || "-"}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                    No leads found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
