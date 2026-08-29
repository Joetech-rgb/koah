import { Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import Leads from "./pages/Leads";
import Drafts from "./pages/Drafts";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="leads" element={<Leads />} />
        <Route path="drafts" element={<Drafts />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}