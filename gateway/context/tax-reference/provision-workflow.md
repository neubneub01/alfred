# Tax Provision Process Workflow

## Phase 1: Planning & Data Gathering (Weeks 1-2)

1. **Obtain trial balance** — Year-end adjusted TB from accounting
2. **Gather PBC items** — Reference pbc-checklist.md
3. **Review prior year provision** — Understand carryforward positions
4. **Identify current year events** — M&A, restructuring, new jurisdictions, law changes
5. **Confirm entity structure** — Any new/dissolved entities?

## Phase 2: Current Tax Computation (Weeks 2-3)

### Federal Current Tax
1. Start with pretax book income
2. Add back permanent differences:
   - Meals (50%)
   - Fines/penalties (100%)
   - Life insurance premiums
   - Non-deductible stock comp (ISOs)
3. Adjust for temporary differences:
   - Depreciation (book vs. MACRS)
   - Accrual adjustments
   - Section 174 R&D capitalization
4. Apply NOL deduction (80% limitation post-TCJA)
5. Compute taxable income
6. Apply federal rate (21%)
7. Apply tax credits (R&D, foreign tax, etc.)
8. = Federal current tax expense

### State Current Tax
1. Start with federal taxable income (or book income per state rules)
2. Apply state modifications (addition/subtraction)
3. Apportion using applicable factors (sales, payroll, property)
4. Apply state rates
5. Apply state credits
6. = State current tax expense by jurisdiction

## Phase 3: Deferred Tax Computation (Weeks 3-4)

1. **Roll forward deferred tax balances** from prior year
2. **Update temporary differences**:
   - New differences identified this year
   - Changes in existing differences
   - Differences that reversed
3. **Apply enacted rates** — use rate expected to apply when differences reverse
4. **Net deferred position** — DTAs vs. DTLs by jurisdiction
5. **Evaluate valuation allowance** — positive vs. negative evidence analysis
6. **Compute deferred tax expense** = change in net deferred position

## Phase 4: Rate Reconciliation (Week 4)

Reconcile statutory to effective rate:
```
Federal statutory rate                21.0%
State taxes, net of federal benefit   +X.X%
Permanent differences                 +/-X.X%
Tax credits                           -X.X%
Valuation allowance change            +/-X.X%
Return-to-provision adjustments       +/-X.X%
Other                                 +/-X.X%
Effective tax rate                    XX.X%
```

## Phase 5: Uncertain Tax Positions (Week 4)

1. Identify positions with uncertainty
2. Apply two-step test (recognition, then measurement)
3. Update FIN 48 / ASC 740-10 reserve schedule
4. Roll forward: opening + additions - settlements - lapses = closing
5. Accrue interest and penalties per company policy

## Phase 6: Financial Statement Disclosures (Week 5)

Required disclosures:
- Components of income tax expense (current/deferred, federal/state/foreign)
- Rate reconciliation
- Significant components of deferred tax assets and liabilities
- Valuation allowance details
- NOL/credit carryforward amounts and expiration dates
- Uncertain tax position roll-forward
- Undistributed earnings of foreign subsidiaries (if applicable)

## Phase 7: Return-to-Provision (Following Year)

1. Compare provision estimates to actual return amounts
2. Record "true-up" adjustments in current year provision
3. Investigate significant variances
4. Update processes to improve future estimates

## Quality Control Checkpoints

- [ ] Tax rates applied are enacted rates (not proposed/expected)
- [ ] NOL utilization respects 80% post-TCJA limitation
- [ ] Valuation allowance analysis documented with specific evidence
- [ ] All intercompany transactions eliminated in consolidation
- [ ] State apportionment ties to supporting schedules
- [ ] Deferred tax roll-forward balances to prior year provision
- [ ] Rate reconciliation mathematically ties
- [ ] FIN 48 interest/penalties computed correctly
