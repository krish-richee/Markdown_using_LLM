import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import TabNav from "./components/TabNav";
import Dashboard from "./pages/Dashboard";
import Planner from "./pages/Planner";
import Actions from "./pages/Actions";
import History from "./pages/History";
import Notifications from "./pages/Notifications";

export default function App() {
  return (
    <div style={{ display:"flex", height:"100vh", background:"#f4f5f7" }}>
      <Sidebar />
      <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>
        <TopBar />
        <TabNav />
        <div style={{ flex:1, overflowY:"auto", padding:"20px" }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/planner"   element={<Planner />} />
            <Route path="/actions"   element={<Actions />} />
            <Route path="/history"   element={<History />} />
            <Route path="/notifications" element={<Notifications />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}