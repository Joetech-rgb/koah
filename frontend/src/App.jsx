import { Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import LeadsTable from "./pages/LeadsTable";
import Drafts from "./pages/Drafts";
import DraftTester from "./pages/DraftTester";
import Settings from "./pages/Settings";
import DigestDetail from "./pages/DigestDetail";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="leads" element={<LeadsTable />} />
        <Route path="drafts" element={<Drafts />} />
        <Route path="draft-tester" element={<DraftTester />} />
        <Route path="reports/:date" element={<DigestDetail />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
