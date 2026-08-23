# Sonoga HMS — Operational Completion Phase

Added in this phase:

- Inventory dashboard, stock ledger, transfers and controlled adjustments.
- Procurement workflow: purchase request -> approval -> purchase order -> goods receipt -> inventory posting.
- Cumulative goods-receipt validation to stop over-receipt against a purchase order.
- Payroll UI: create run, generate active employees, adjust earnings/deductions, approve and mark paid.
- Unified approval centre for submitted expenses, purchase requests and generated payroll.
- Operational notification centre for low stock, pending approvals, housekeeping, maintenance and payroll.
- Read-only audit-log interface for Group Management and Auditor roles.
- Date-range consolidated Sonoga Group report with CSV export.
- Business-unit URL scoping for purchasing and payroll records.
- Expanded navigation so daily users no longer depend on Django Admin for these workflows.
- Final setup guide for migration, bootstrap, seed data, staff creation and WordPress bridge binding.

The public online booking flow remains in WordPress. The Django HMS continues to receive synchronized booking/payment events through the signed API endpoint.
