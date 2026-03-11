# Common Deferred Tax Scenarios & Patterns

## Pattern 1: Accelerated Depreciation (DTL)

**Situation**: Company uses straight-line for books, MACRS for tax.
**Year 1**: Tax depreciation > Book depreciation → taxable income < book income → DTL
**Reversal**: Later years when book depreciation > tax depreciation

**Journal Entry (Year 1)**:
```
Dr. Tax Expense (deferred)     XXX
  Cr. Deferred Tax Liability     XXX
```

**Key rates**: Apply enacted rate to temporary difference balance.

## Pattern 2: Accrued Liabilities (DTA)

**Situation**: Company accrues warranty/bonus/vacation expense for books. Tax deduction only when paid.
**Year 1**: Book expense recognized, no tax deduction → DTA
**Reversal**: When liability is paid (cash basis for tax)

**Watch for**: 2½ month rule on bonuses (must be paid within 2½ months of year-end for accrual basis deduction).

## Pattern 3: Bad Debt Reserve (DTA)

**Situation**: GAAP uses allowance method; tax uses direct write-off.
**Effect**: Reserve balance × tax rate = DTA
**Reversal**: When specific accounts are written off

## Pattern 4: NOL Carryforward (DTA)

**Post-TCJA Rules**:
- NOLs generated after 12/31/2017: 80% limitation, indefinite carryforward
- Pre-2018 NOLs: 20-year carryforward, no percentage limitation

**Valuation Allowance**: Most common VA trigger. Evaluate positive vs. negative evidence.

**Scheduling**: Must demonstrate sufficient future taxable income to utilize NOLs.

## Pattern 5: Section 174 R&D Capitalization (DTL)

**Effective 2022+**: All Section 174 expenditures must be capitalized.
- Domestic: Amortize over 5 years (mid-year convention)
- Foreign: Amortize over 15 years
**Effect**: Book expenses immediately, tax amortizes → DTL in early years
**Year 1**: Only 10% deductible (½ year × 1/5) for domestic

## Pattern 6: ASC 842 Leases

**Operating Leases**:
- Book: ROU asset and lease liability recognized
- Tax: Cash rent payments deductible
- Creates both DTA (liability > asset amortization) and DTL (asset > liability)
- Net effect usually small but must track separately

## Pattern 7: Stock Compensation

**RSUs/NSOs**:
- Book: Expense over vesting period (ASC 718 fair value)
- Tax: Deduction at exercise/vest for intrinsic value
- Creates DTA during vesting period
- "Windfall" or "shortfall" at settlement if stock price differs from grant-date fair value

**ISOs**: Generally no tax deduction (exception: disqualifying disposition)
- Book expense recognized → permanent difference (add back)

## Pattern 8: Goodwill

**Tax-deductible goodwill** (asset deal / 338(h)(10)):
- Tax: Amortize over 15 years (Section 197)
- Book: Not amortized, tested for impairment
- Creates indefinite-lived DTL (never reverses unless asset sold/impaired)

**Non-deductible goodwill** (stock deal):
- No temporary difference (both bases equal or tax basis = 0)
- Book impairment → permanent difference

## Pattern 9: State Tax Provisions

**Approach**: Calculate state provision separately or use blended state rate.
**Blended rate**: Weighted average of state rates based on apportionment
**Federal benefit**: State taxes are deductible for federal → adjust blended rate:
  `Effective state rate = blended state rate × (1 - federal rate)`

## Pattern 10: Business Combinations (M&A)

**Purchase accounting**: Fair value step-up creates new temporary differences
- Acquired DTAs/DTLs recorded at acquisition date
- Goodwill = residual (may be deductible or not depending on structure)
- Tax basis may differ significantly from book fair values
- **Key**: Identify all Day 1 temporary differences from purchase price allocation
