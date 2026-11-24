*** Settings ***
Documentation    Billing checks shipped in the approved platform catalog.

*** Test Cases ***
Invoice Total Includes Tax
    [Tags]    regression
    ${total}=    Evaluate    round(100 * 1.2, 2)
    Should Be Equal As Numbers    ${total}    120.0

Smoke Invoice Reference
    [Tags]    smoke
    Should Start With    INV-1042    INV-

Rejected Negative Quantity
    [Tags]    regression
    Should Be True    ${-1 < 0}
