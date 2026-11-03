import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Shell from "./Shell";
import "./styles.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <Shell />
  </StrictMode>,
);
