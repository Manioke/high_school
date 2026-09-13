# School Finance Setup and Demo Guide

This guide configures ERPNext v16 and Frappe HR v16 as the accounting source for the High School Executive Dashboard. The app does not maintain a second ledger. It reads submitted General Ledger entries, Budgets, Sales Invoices, and Frappe HR payroll records.

## 1. Accounting model

Use one ERPNext Company for the school. Example:

- Company: `Queen Salote College`
- Abbreviation: `QSC`
- Default currency: the school's accounting currency
- Fiscal Year: create the year containing the School Term dates

Create this Cost Center tree:

- `Main - QSC` — group Cost Center for the whole school
  - `Administration - QSC` — non-group posting Cost Center
  - `Teaching - QSC` — non-group posting Cost Center
  - `Science Lab - QSC` — non-group posting Cost Center
  - `Boarding - QSC` — non-group posting Cost Center
  - `Maintenance - QSC` — non-group posting Cost Center

Set **School Finance Cost Center** to `Main - QSC`. This is correct when it is the parent of all school operational Cost Centers. Enter transactions against the appropriate non-group child. The Executive Dashboard expands the configured group and includes its descendants.

Create or confirm these leaf Accounts under the normal ERPNext account groups:

| Type | Suggested account |
|---|---|
| Income | Student Fee Income - QSC |
| Income | Grants and Donations - QSC |
| Income | Other School Income - QSC |
| Expense | Electricity Expense - QSC |
| Expense | Water Expense - QSC |
| Expense | Internet Expense - QSC |
| Expense | Science Lab Supplies - QSC |
| Expense | Teaching Materials - QSC |
| Expense | Employee Wages - QSC |
| Expense | Repairs and Maintenance - QSC |
| Expense | Boarding Food - QSC |
| Liability | Payroll Payable - QSC |
| Asset | School Bank Account - QSC |
| Asset | Cash - QSC |

Use the standard Debtors and Creditors control accounts created for the Company. Do not post operational transactions directly to group accounts.

## 2. School MIS Settings

In **School MIS Settings → Executive Finance Targets**:

1. Enable **Track Whole-School Finance**.
2. Set **School Finance Company** to `Queen Salote College`.
3. Set **School Finance Cost Center** to `Main - QSC`.
4. Set **Student Fee Income Account** to `Student Fee Income - QSC`.
5. Set **Employee Wages Expense Account** to `Employee Wages - QSC`. A parent wages group is also valid if salary components use child accounts.
6. Enable **Track Frappe HR Payroll**.
7. Set **Payroll Payable Account** to `Payroll Payable - QSC`.

The selected School Term controls the dates used for term income and term expenses. For a current term, the dashboard reports through today. For a completed term, it reports through the term end. If a future School Term is deliberately selected for demonstration data, the dashboard enters a clearly labelled preview and includes submitted future-dated entries through the term end. Cash and bank is the company-wide balance at that reporting date. A school can therefore have zero current-term income, positive cash carried from an earlier term, and current-term expenses greater than zero.

## 3. Budgets

For a simple demonstration, create one submitted Budget for each leaf Cost Center and expense Account:

| Budget | Cost Center | Account | Annual amount |
|---|---|---|---:|
| Administration utilities | Administration - QSC | Electricity Expense - QSC | 12,000 |
| Science programme | Science Lab - QSC | Science Lab Supplies - QSC | 8,000 |
| Teaching resources | Teaching - QSC | Teaching Materials - QSC | 15,000 |
| Maintenance | Maintenance - QSC | Repairs and Maintenance - QSC | 10,000 |

The Budget must be submitted, belong to the configured Company, and cover the Fiscal Year containing the dashboard's selected School Term. Budget Actual is fiscal-year-to-reporting-date, while Term Expenses only covers the selected School Term. A Budget only compares against matching GL entries: Company, date, Account, and Cost Center must all match its scope.

## 4. Electricity bill scenario

1. Create a non-stock service Item called `Electricity Bill`.
2. Set its default expense Account to `Electricity Expense - QSC`.
3. Create a Purchase Invoice for the electricity supplier.
4. On the Purchase Invoice item row, verify:
   - Expense Account = `Electricity Expense - QSC`
   - Cost Center = `Administration - QSC`
   - Posting Date falls inside the selected School Term and the Budget Fiscal Year
   - Amount = 1,000 for this example
5. Submit the Purchase Invoice.
6. Open General Ledger and confirm a debit of 1,000 to `Electricity Expense - QSC` with `Administration - QSC`.

Expected dashboard result after refresh:

- Term Expenses increases by 1,000.
- Expense Entries includes Electricity Expense / Administration.
- The Administration electricity Budget shows 1,000 actual and 11,000 remaining.
- Term Income does not need to be greater than zero.

Create and submit a Payment Entry afterward. The payment reduces the bank balance and the supplier payable. It does not create the electricity expense a second time.

## 5. Science laboratory supplies scenario

For the clearest demo, use a non-stock consumable Item:

1. Create `Science Lab Consumables` as a non-stock Item.
2. Set Expense Account to `Science Lab Supplies - QSC`.
3. Create and submit a Purchase Invoice for 2,000.
4. Set the item-row Cost Center to `Science Lab - QSC`.
5. Confirm the expense debit in General Ledger.

Expected result: term expenses increase by 2,000 and the Science Lab Budget shows 2,000 used and 6,000 remaining.

If perpetual inventory is enabled and a stock Item is purchased, the purchase may initially debit an inventory Asset Account instead of an Expense Account. In that design, the budgeted expense appears only when stock is consumed through the appropriate stock/accounting process. Use a non-stock consumable for the simple board demonstration.

## 6. Payroll scenario with Frappe HR v16

1. Create Employees, Salary Components, Salary Structures, and Salary Structure Assignments.
2. Map earning Salary Components to `Employee Wages - QSC` or suitable child wage accounts.
3. Set Payroll Payable Account to `Payroll Payable - QSC` in the relevant HR/Company payroll settings.
4. Set Cost Centers deliberately. Frappe HR uses the most specific configured source; Salary Structure Assignment, Employee, Department, and Payroll Entry settings can affect the final Cost Center. Verify the generated Journal Entry.
5. Create a Payroll Entry whose start/end dates overlap the selected School Term.
6. Get Employees and create Salary Slips.
7. Use **Submit Salary Slips** from the Payroll Entry. This creates the payroll accrual Journal Entry.
8. Submit the generated accrual Journal Entry and confirm:
   - debit to Employee Wages expense Account(s)
   - credit to Payroll Payable
   - a Cost Center inside `Main - QSC`
9. Use **Make Bank Entry** from Payroll Entry and submit it to pay employees.

Expected result:

- Payroll Processed shows submitted Salary Slip net pay.
- The payroll detail also shows gross pay and the posted wage expense separately. Net pay normally differs from wage expense because deductions and employer components affect the accounting entry.
- When Salary Slip has no Cost Center field, the dashboard scopes its operational totals through the linked Payroll Entry. Salary budget actual and Wage Expense always come from the General Ledger Cost Center on the posted accrual.
- Term Expenses and Wage Expense rise when the payroll accrual GL entry is posted.
- Payroll Payable remains visible until the salary Bank Entry is submitted.
- Cash and bank falls when the Bank Entry is submitted.

Submitting Salary Slips individually outside Payroll Entry can leave payroll operational records without the bulk payroll accrual Journal Entry. For this dashboard, always run the complete Payroll Entry workflow.

## 7. Student fee scenario

1. Create and submit student Sales Invoices with a posting date inside the School Term and the correct education/student link used by the app.
2. Use `Student Fee Income - QSC` as the income Account and a Cost Center under `Main - QSC`.
3. A submitted unpaid invoice increases invoiced and outstanding amounts; it does not count as collected.
4. Submit a Payment Entry allocated against the Sales Invoice.

Expected result: collected is calculated as submitted invoice total minus its outstanding balance. An overdue unpaid invoice remains outstanding and appears for follow-up.

## 8. Fund request demonstration

Create a School Fund Request for new science equipment, assign `Science Lab - QSC`, and record the requested and approved amounts. Progress only represents the documented request/approval/disbursement process. When marking it disbursed, link submitted ERPNext accounting evidence such as a Purchase Invoice, Payment Entry, or Journal Entry.

## 9. If Budget Actual or Term Expenses still shows zero

Check in this order:

1. The Purchase Invoice or Journal Entry is submitted, not Draft.
2. The Posting Date is inside both the selected School Term and relevant Fiscal Year.
3. General Ledger shows a debit to the exact intended Expense Account.
4. The GL row has the intended leaf Cost Center.
5. That Cost Center is the configured `Main - QSC` or one of its descendants.
6. The Budget is submitted and belongs to the same Company and Fiscal Year.
7. The Budget Account contains the GL Account and the Budget Cost Center contains the GL Cost Center.
8. Report filters are not hiding the voucher.

The dashboard's **Term Profit and Loss Detail** table is the quickest audit trail. If the expected row is absent, inspect the submitted voucher in General Ledger. Also compare the displayed reporting range: a future term must be shown as a preview, never as a reversed date range. A Payment Entry by itself cannot make Budget Actual increase because it settles the liability; the Purchase Invoice or expense Journal Entry creates the expense.
