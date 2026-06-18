import { StrictMode }  from "react";
import { createRoot }  from "react-dom/client";
import "./styles/global.css";
import LHCViewer       from "./LHCViewer";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <LHCViewer />
  </StrictMode>
);