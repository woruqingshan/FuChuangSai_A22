import "./styles.css";

import { bootstrapCompanionApp } from "./app/bootstrapCompanionApp";
import { renderLandingPage } from "./pages/landingPage";

const root = document.getElementById("app");
const pathname = window.location.pathname.replace(/\/+$/, "") || "/";

if (pathname === "/app") {
  document.body.dataset.page = "app";
  bootstrapCompanionApp({ root });
} else if (pathname === "/") {
  document.body.dataset.page = "landing";
  renderLandingPage({ root });
} else {
  document.body.dataset.page = "landing";
  renderLandingPage({ root, notFoundPath: window.location.pathname });
}
