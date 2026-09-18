import { Routes, Route, Link } from "react-router-dom";
import PublicWidget from "./views/PublicWidget";
import MediaIntake from "./views/MediaIntake";
import ReviewConsole from "./views/ReviewConsole";
import CuratorAdmin from "./views/CuratorAdmin";
import AuditLog from "./views/AuditLog";

// Routes for all 5 views are wired here as part of the project scaffold. Feature
// branches fill in their own view component (src/views/*.tsx) and should not need
// to edit this file. The role switcher / real auth-gating is specs/011's job.
export default function App() {
  return (
    <div>
      <nav>
        <Link to="/">Public</Link> | <Link to="/media">Media</Link> |{" "}
        <Link to="/review">Review</Link> | <Link to="/curator">Curator Admin</Link> |{" "}
        <Link to="/audit">Audit Log</Link>
      </nav>
      <Routes>
        <Route path="/" element={<PublicWidget />} />
        <Route path="/media" element={<MediaIntake />} />
        <Route path="/review" element={<ReviewConsole />} />
        <Route path="/curator" element={<CuratorAdmin />} />
        <Route path="/audit" element={<AuditLog />} />
      </Routes>
    </div>
  );
}
