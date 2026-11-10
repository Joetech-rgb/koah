import { useState } from "react";
import client from "../api/client";

export default function DraftTester() {
  const [form, setForm] = useState({ company_name: "", domain: "", country: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await client.post("agent/research-and-draft/", form);
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-[#10193A] mb-4">Draft Tester</h1>

      <form onSubmit={handleSubmit} className="space-y-4 bg-white p-6 rounded-lg shadow">
        <div>
          <label className="block text-sm font-medium text-[#10193A] mb-1">Company Name</label>
          <input
            type="text"
            name="company_name"
            value={form.company_name}
            onChange={handleChange}
            required
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#3FB8AA]"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[#10193A] mb-1">Domain (optional)</label>
          <input
            type="text"
            name="domain"
            value={form.domain}
            onChange={handleChange}
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#3FB8AA]"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[#10193A] mb-1">Country (optional)</label>
          <input
            type="text"
            name="country"
            value={form.country}
            onChange={handleChange}
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#3FB8AA]"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="bg-[#3FB8AA] text-white px-4 py-2 rounded font-medium hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Researching & Drafting... (10-30s)" : "Research & Draft"}
        </button>
      </form>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 bg-white p-6 rounded-lg shadow space-y-3">
          <div className="flex gap-4 text-sm">
            <span className="bg-[#10193A] text-white px-2 py-1 rounded">
              Industry: {result.detected_industry}
            </span>
            <span className="bg-[#3FB8AA] text-white px-2 py-1 rounded">
              Has Website: {result.has_website ? "Yes" : "No"}
            </span>
            <span className="bg-gray-600 text-white px-2 py-1 rounded">
              Angle: {result.pitch_angle}
            </span>
          </div>
          <div>
            <h3 className="font-semibold text-[#10193A]">Subject</h3>
            <p className="text-gray-800">{result.subject}</p>
          </div>
          <div>
            <h3 className="font-semibold text-[#10193A]">Body</h3>
            <p className="text-gray-800 whitespace-pre-wrap">{result.body}</p>
          </div>
        </div>
      )}
    </div>
  );
}
