# StockPilot frontend

A React 18 + TypeScript operations workspace built with Vite 8. All application data comes from the FastAPI service. The eight views cover the overview dashboard, product catalog and warehouse balances, stock movements, purchase orders, reservations, warehouse network, suppliers, and background reports.

```bash
npm ci
npm test
npm run build
npm run dev
```

Development uses port 5173 and proxies `/api` to `http://127.0.0.1:8000`. Set `API_TARGET` to change the target. The production image serves the compiled application through unprivileged Nginx on port 8080 and proxies `/api`, `/docs`, and `/openapi.json` to `backend:8000`.

The product catalog reads every 200-record API page before allowing global catalog search and product selection. The movement ledger displays the latest 200 movements. Supplier, warehouse, reservation, and purchase-order listings follow the API's current record limits. These views refresh after successful mutations or with the toolbar refresh action.

Stock operations retain an idempotency key when retrying an unchanged form payload. Keys work on both HTTPS and local-cluster HTTP. CSV exports quote fields and neutralize spreadsheet formula prefixes. Modals provide keyboard focus containment, Escape dismissal, and accessible labels; data failures remain visible in the workspace.

`npm test` runs Node's test runner with jsdom and React Testing Library, without opening a network socket. These tests verify UI behavior against explicit API-response fixtures; they are not browser-rendering or deployed-service tests. Backend integration tests verify the actual database and inventory transitions separately. Node 24 is used by CI and the Docker build. The interface uses system font fallbacks when its optional Google Fonts stylesheet is unavailable.
