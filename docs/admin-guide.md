# AI Offer Agent - Administrator Guide

Complete guide for administrators managing the AI Offer Agent system, including approval workflows, offer management, and system administration.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Approval Workflows](#approval-workflows)
4. [Offer Management](#offer-management)
5. [Customer Management](#customer-management)
6. [Analytics & Reporting](#analytics--reporting)
7. [System Configuration](#system-configuration)
8. [User Management](#user-management)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Getting Started

### First-Time Login

1. Navigate to: `https://app.aigentics-corp.com/admin`
2. Log in with admin credentials
3. Complete 2FA setup (required)
4. Set notification preferences

### Admin Dashboard Access

**URL**: `https://app.aigentics-corp.com/admin`

**Required Permissions**:
- Admin Role: Full system access
- Approver Role: Approval workflow access
- Analyst Role: Read-only analytics access

### Navigation

**Main Sections**:
- **Dashboard**: Overview metrics
- **Approvals**: Pending approval requests
- **Offers**: All offers in system
- **Customers**: Customer database
- **Analytics**: Performance metrics
- **Settings**: System configuration

## Dashboard Overview

### Key Metrics Displayed

**Real-time Metrics**:
```
┌─────────────────────────────────────────────────────────────┐
│  Active Conversations: 12                                    │
│  Pending Approvals: 3                                        │
│  Offers Generated Today: 8                                   │
│  Acceptance Rate (30d): 67%                                  │
└─────────────────────────────────────────────────────────────┘
```

**Performance Indicators**:
- Average offer generation time
- API response times
- System health status
- Active user count

**Financial Overview**:
- Total offer value (pending)
- Accepted offers value (this month)
- Pipeline value
- Average deal size

### Alerts & Notifications

**Priority Alerts**:
- High-value offers pending approval (>€100k)
- Offers expiring soon (within 3 days)
- System performance issues
- Failed API calls
- GDPR requests pending

**Notification Channels**:
- In-app notifications (real-time)
- Email alerts (configurable)
- SMS for critical alerts
- Webhook integrations

## Approval Workflows

### Understanding Approval Requirements

**Automatic Approval**:
- Offers ≤ €100,000
- Standard terms and conditions
- No custom pricing

**Manual Approval Required**:
- Offers > €100,000
- Custom pricing or discounts
- Non-standard terms
- High-risk projects

### Reviewing Pending Approvals

**Access**: Dashboard → Approvals → Pending

**List View**:
```
┌──────────┬─────────────────┬──────────────┬───────────┬─────────┐
│ Offer #  │ Customer        │ Value        │ Submitted │ Age     │
├──────────┼─────────────────┼──────────────┼───────────┼─────────┤
│ 25-0042  │ Acme Corp       │ €125,000     │ 2h ago    │ URGENT  │
│ 25-0041  │ TechStart GmbH  │ €89,500      │ 1d ago    │ Normal  │
│ 25-0039  │ Global Inc      │ €215,000     │ 3h ago    │ URGENT  │
└──────────┴─────────────────┴──────────────┴───────────┴─────────┘
```

**Priority Indicators**:
- 🔴 Red: >€200k or >24h old
- 🟡 Yellow: €100k-€200k or >12h old
- 🟢 Green: Recently submitted

### Approval Process

#### Step 1: Review Offer Details

Click on offer to view:

**Offer Summary**:
- Customer information
- Project overview
- Total value breakdown
- Work packages
- Timeline estimate
- Payment terms

**Quality Checks**:
- ✅ Requirements completeness
- ✅ Pricing consistency
- ✅ Deliverables clarity
- ✅ Legal compliance
- ✅ Resource availability

#### Step 2: Review Work Packages

Each work package shows:
```
Work Package: Requirements Analysis & Design
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Description: Comprehensive analysis of CRM requirements...

Deliverables:
  • Requirements Document (acceptance criteria)
  • Technical Architecture Design
  • Prototype Mockups

Estimated Hours: 120h (PERT: 80h optimistic, 160h pessimistic)
Confidence: 85%
Hourly Rate: €150/h
Total Cost: €18,000

Dependencies: None
Risk Level: Low
```

**Review Checklist**:
- [ ] Deliverables are clearly defined
- [ ] Hours estimation is realistic
- [ ] Pricing aligns with company rates
- [ ] Dependencies are identified
- [ ] Acceptance criteria are measurable

#### Step 3: Make Decision

**Three Options**:

**1. Approve**
```
Decision: Approve
Comments: Approved. Standard CRM project with clear scope.
Modifications: None
```

**2. Approve with Modifications**
```
Decision: Approve with Changes
Comments: Reduce hours for testing phase
Modifications:
  - Work Package 4: Reduce from 80h to 60h
  - Update total: €125,000 → €122,000
```

**3. Reject or Request Revision**
```
Decision: Needs Revision
Comments: Scope too broad. Please clarify integration requirements.
Required Changes:
  - Split Work Package 3 into two separate packages
  - Add detailed integration specification
  - Clarify third-party API costs
```

#### Step 4: Submit Review

**Approval Actions**:
1. Click "Approve" or "Request Changes"
2. Add comments (required)
3. Specify modifications if any
4. Click "Submit Review"

**What Happens Next**:
- Offer status updated
- Customer notified (if approved)
- Sales team alerted (if changes needed)
- Audit log entry created

### Batch Approval

For multiple offers:

1. Select offers using checkboxes
2. Click "Batch Actions" → "Approve Selected"
3. Confirm action
4. All selected offers approved simultaneously

**Use Case**: Multiple low-value offers (<€50k) from approved customers

**Safety**: Batch approval limited to offers meeting strict criteria

## Offer Management

### Viewing All Offers

**Access**: Dashboard → Offers

**Filters**:
- Status: Draft, Pending, Approved, Sent, Accepted, Rejected
- Date Range: Last 7/30/90 days or custom
- Value Range: €0-50k, €50k-100k, €100k+
- Customer: Search by name
- Assigned To: Filter by sales rep

**Export Options**:
- CSV for Excel analysis
- PDF for printing
- JSON for API integration

### Offer Details View

**Information Sections**:

**1. Basic Information**
- Offer number and version
- Creation date
- Valid until date
- Current status
- Customer details

**2. Financial Summary**
- Work packages breakdown
- Hourly rates by role
- Total estimated hours
- Subtotal and total
- Tax calculation
- Payment terms

**3. Technical Details**
- Project category
- Technologies mentioned
- Complexity score
- Risk assessment
- Resource requirements

**4. History & Audit Trail**
- Status changes
- Approval events
- Modifications log
- Customer interactions
- Email/PDF downloads

### Modifying Offers

**Editable After Approval**:
- Validity date extension
- Minor text corrections
- Customer contact updates

**Requires New Version**:
- Work package changes
- Pricing modifications
- Scope adjustments

**To Create New Version**:
1. Open offer
2. Click "Create New Version"
3. Make changes
4. Save as draft
5. Re-submit for approval if needed

### Sending Offers to Customers

**Manual Send**:
1. Open approved offer
2. Click "Send to Customer"
3. Review email template
4. Modify email if needed
5. Click "Send"

**Automatic Send** (if configured):
- Approved offers sent automatically
- 1-hour delay for last-minute checks
- Email notification to admin

**Email Template**:
```
Subject: Your IT Consulting Offer - [Offer Number]

Dear [Customer Name],

Thank you for your interest in our services. We're pleased to present
your customized offer for [Project Name].

[Offer Summary]

To download your complete offer document, please click:
[Download PDF Button]

This offer is valid until [Valid Until Date].

If you have any questions, please don't hesitate to contact us.

Best regards,
[Sales Rep Name]
```

### Tracking Offer Status

**Status Lifecycle**:
```
Draft → Pending Approval → Approved → Sent → Viewed → Accepted/Rejected
```

**Status Indicators**:
- **Draft**: 🟡 Created but not submitted
- **Pending Approval**: 🟠 Awaiting admin review
- **Approved**: 🟢 Ready to send
- **Sent**: 📧 Delivered to customer
- **Viewed**: 👁️ Customer opened PDF
- **Accepted**: ✅ Customer accepted
- **Rejected**: ❌ Customer declined
- **Expired**: ⏰ Past validity date

**Viewing Tracking**:
- PDF downloads tracked
- Open timestamps recorded
- Multiple views logged
- Time to decision measured

## Customer Management

### Customer Database

**Access**: Dashboard → Customers

**Information Stored**:
- Company name
- Contact person(s)
- Email and phone
- Address
- Industry
- Company size
- GDPR consent status
- Conversation history
- Offers history

### Adding New Customer

**Manual Entry**:
1. Click "Add Customer"
2. Fill required fields:
   - Company name (required)
   - Contact person (required)
   - Email (required)
   - Phone (optional)
   - Address (optional)
3. GDPR consent (required)
4. Click "Save"

**Automatic Creation**:
- Created during conversation
- Customer data captured progressively
- Consent obtained during flow

### GDPR Management

**Consent Tracking**:
```
GDPR Consent Status: ✅ Active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Given: 2025-10-06 15:30:00
Version: 1.0
Purposes:
  ✓ Offer generation
  ✓ Communication
  ✓ Marketing (opted out)

Data Processing:
  Location: EU (Germany)
  Retention: 7 years (legal requirement)
  Encryption: AES-256
```

**Handling GDPR Requests**:

**1. Right to Access**:
- Customer requests their data
- Admin: Customer → [Name] → "Export Data"
- System generates JSON with all data
- Delivered within 30 days

**2. Right to Erasure**:
- Customer requests deletion
- Admin: Customer → [Name] → "Process Deletion Request"
- Review: Check for legal retention requirements
- Approve deletion
- System pseudonymizes data
- Confirmation sent to customer

**3. Right to Rectification**:
- Customer requests correction
- Admin edits customer record
- Changes logged in audit trail

### Viewing Customer History

**Timeline View**:
```
2025-10-06 15:30 | Conversation started
2025-10-06 16:15 | Conversation completed (85%)
2025-10-06 16:30 | Offer generated (#25-0042)
2025-10-06 17:00 | Offer approved by admin
2025-10-06 17:15 | Offer sent to customer
2025-10-07 09:30 | PDF downloaded by customer
2025-10-07 10:00 | Customer accepted offer
```

**Statistics**:
- Total conversations: 3
- Offers generated: 2
- Acceptance rate: 100%
- Total value: €215,000
- Average response time: 18 hours

## Analytics & Reporting

### Dashboard Analytics

**Conversion Funnel**:
```
Conversations Started:     500 ┃████████████████████┃ 100%
Conversations Completed:   385 ┃███████████████     ┃  77%
Offers Generated:          320 ┃████████████        ┃  64%
Offers Sent:               280 ┃███████████         ┃  56%
Offers Accepted:           156 ┃██████              ┃  31%
```

**Key Metrics**:
- Conversion rate: 31% (conversations → accepted offers)
- Average time to offer: 45 minutes
- Average time to decision: 4.2 days
- Approval rate: 87%

### Offer Performance

**Metrics Tracked**:
- Generation time (target: <30s)
- Approval time (target: <24h)
- Customer response time
- Acceptance rate by category
- Average offer value

**Time Series Charts**:
- Offers per day/week/month
- Value trends
- Acceptance trends
- Response time trends

### Custom Reports

**Creating Report**:
1. Analytics → Reports → New Report
2. Select metrics:
   - Offers by status
   - Revenue by month
   - Conversion rates
   - Customer segments
3. Set date range
4. Apply filters
5. Click "Generate"

**Export Formats**:
- PDF for presentation
- CSV for Excel
- JSON for integration

**Scheduled Reports**:
- Daily summary (email at 9 AM)
- Weekly report (Monday 8 AM)
- Monthly report (1st of month)

### Financial Analytics

**Revenue Tracking**:
```
Current Month: October 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Offers Generated:     32
Total Value:          €2,840,000
Accepted:             18
Accepted Value:       €1,560,000
Pipeline:             14 (€1,280,000)

Acceptance Rate:      56%
Avg Offer Value:      €88,750
Avg Accepted Value:   €86,667
```

**Trend Analysis**:
- Month-over-month growth
- Quarter-over-quarter comparison
- Year-to-date performance
- Forecast based on pipeline

## System Configuration

### General Settings

**Access**: Dashboard → Settings → General

**Configurable Options**:
- Company information
- Default language
- Timezone
- Currency
- Date format
- Business hours

### Approval Thresholds

**Configure Approval Rules**:
```
Approval Rules Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Auto-approve up to:          €100,000
Requires approval above:     €100,000
Requires senior approval:    €500,000
Requires board approval:     €1,000,000

Custom pricing:              Always requires approval
Non-standard terms:          Always requires approval
High-risk projects:          Always requires approval
```

### Email Templates

**Customizable Templates**:
- Approval required notification
- Offer sent to customer
- Offer accepted confirmation
- Offer rejected notification
- GDPR request confirmation

**Template Variables**:
- `{customer_name}`
- `{offer_number}`
- `{total_value}`
- `{valid_until}`
- `{company_name}`

**Editing Template**:
1. Settings → Email Templates
2. Select template
3. Edit subject and body
4. Preview with sample data
5. Test send to your email
6. Save changes

### Integration Settings

**External Services**:
- OpenAI API key management
- Email service (SMTP) configuration
- Webhook URLs
- Analytics tracking
- CRM integration

**API Keys**:
- View current keys
- Generate new keys
- Rotate keys
- Revoke keys
- Set permissions per key

### Notification Preferences

**Per-User Settings**:
```
Notification Preferences
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Email Notifications:
  ✓ New approval requests
  ✓ High-value offers (>€200k)
  ✓ Offers expiring soon
  ✓ GDPR requests
  □ Daily summary

In-App Notifications:
  ✓ All approval events
  ✓ Offer status changes
  ✓ System alerts

SMS Alerts (Critical Only):
  ✓ System outages
  □ High-priority approvals
```

## User Management

### Admin Users

**Access**: Dashboard → Settings → Users

**User Roles**:
- **Super Admin**: Full system access
- **Admin**: All features except user management
- **Approver**: Approval workflows only
- **Analyst**: Read-only analytics
- **Sales**: Customer-facing features only

### Adding New User

1. Click "Add User"
2. Enter details:
   - Name
   - Email
   - Role
   - Department
3. Set permissions
4. Send invitation email
5. User receives setup link

### User Permissions Matrix

```
┌──────────────────┬───────┬───────┬──────────┬─────────┬───────┐
│ Feature          │ Super │ Admin │ Approver │ Analyst │ Sales │
│                  │ Admin │       │          │         │       │
├──────────────────┼───────┼───────┼──────────┼─────────┼───────┤
│ View Dashboard   │   ✓   │   ✓   │    ✓     │    ✓    │   ✓   │
│ Approve Offers   │   ✓   │   ✓   │    ✓     │    ✗    │   ✗   │
│ Edit Offers      │   ✓   │   ✓   │    ✗     │    ✗    │   ✓   │
│ View Analytics   │   ✓   │   ✓   │    ✓     │    ✓    │   ✗   │
│ Manage Customers │   ✓   │   ✓   │    ✗     │    ✗    │   ✓   │
│ System Settings  │   ✓   │   ✗   │    ✗     │    ✗    │   ✗   │
│ User Management  │   ✓   │   ✗   │    ✗     │    ✗    │   ✗   │
└──────────────────┴───────┴───────┴──────────┴─────────┴───────┘
```

### Managing User Access

**Deactivating User**:
1. Users → Select user
2. Click "Deactivate"
3. Confirm action
4. User cannot log in
5. Data preserved for audit

**Resetting Password**:
1. Users → Select user
2. Click "Reset Password"
3. User receives email
4. Must set new password

### Audit Logging

**All Actions Logged**:
- User logins/logouts
- Offer approvals/rejections
- Customer data access
- Configuration changes
- Export operations
- GDPR requests

**Viewing Audit Log**:
1. Settings → Audit Log
2. Filter by:
   - User
   - Action type
   - Date range
3. Export for compliance

## Troubleshooting

### Common Issues

**1. Offer Generation Takes Too Long**

**Symptoms**: Generation >30 seconds

**Checks**:
- Dashboard → System Health
- Check OpenAI API status
- Review recent errors in logs

**Resolution**:
- Contact technical support
- Check API rate limits
- Restart services if needed

**2. Email Not Received**

**Symptoms**: Customer didn't receive offer email

**Checks**:
- Settings → Email → Test Connection
- Check spam folder
- Verify customer email address
- Review email logs

**Resolution**:
- Resend offer: Offer → Actions → Resend Email
- Update email address if incorrect
- Check SMTP configuration

**3. Approval Notification Not Received**

**Symptoms**: Admin didn't receive approval alert

**Checks**:
- Your notification preferences
- Email service status
- Check notification queue

**Resolution**:
- Update preferences
- Check spam folder
- Contact support if persistent

**4. Cannot Access Analytics**

**Symptoms**: Analytics page shows error

**Checks**:
- User permissions
- System health dashboard
- Browser console errors

**Resolution**:
- Refresh page
- Clear browser cache
- Check with Super Admin for permissions

### Getting Help

**Support Channels**:
- **Documentation**: https://docs.aigentics-corp.com
- **Email Support**: admin-support@aigentics-corp.com
- **Phone**: +49 30 1234-5678 (9 AM - 5 PM CET)
- **Emergency**: +49 30 1234-9999 (24/7)

**Before Contacting Support**:
1. Check this guide
2. Review system status page
3. Check audit logs for errors
4. Take screenshot of issue
5. Note time of occurrence

**Information to Provide**:
- Your admin username
- Time and date of issue
- Steps to reproduce
- Screenshot or error message
- Browser and version

## Best Practices

### Approval Workflows

**Response Time Targets**:
- Standard offers (<€150k): Review within 12 hours
- High-value offers (€150k-€500k): Review within 6 hours
- Critical offers (>€500k): Review within 2 hours

**Quality Checks**:
- Always verify customer requirements
- Check pricing against standard rates
- Ensure deliverables are measurable
- Confirm resource availability
- Review risk assessment

**Communication**:
- Add detailed comments to all decisions
- Use templates for common feedback
- CC relevant stakeholders
- Follow up on revisions within 24h

### Offer Management

**Regular Reviews**:
- Check pending approvals daily
- Review offers expiring within 7 days
- Follow up on sent offers after 3 days
- Archive rejected/expired offers monthly

**Data Quality**:
- Keep customer data updated
- Tag offers by project type
- Assign offers to sales reps
- Document custom terms

### Customer Relations

**Privacy First**:
- Only access customer data when necessary
- Always obtain consent before processing
- Process GDPR requests promptly
- Document all data access

**Communication**:
- Use professional, friendly tone
- Respond to inquiries within 4 hours
- Keep customers informed of status
- Follow up after offer acceptance

### System Maintenance

**Daily**:
- Review dashboard alerts
- Check pending approvals
- Monitor system health

**Weekly**:
- Review analytics trends
- Check for stale offers
- Update user permissions if needed

**Monthly**:
- Generate performance report
- Review and optimize workflows
- Update email templates if needed
- Audit user access logs

### Security

**Access Control**:
- Use strong passwords (min 12 characters)
- Enable 2FA (required)
- Don't share credentials
- Log out when finished

**Data Protection**:
- Only export data when necessary
- Delete exported files after use
- Report suspicious activity immediately
- Review audit logs regularly

### Performance Optimization

**Tips for Faster Workflows**:
- Use keyboard shortcuts
- Set up custom filters
- Create saved views
- Use batch operations
- Schedule reports

**Keyboard Shortcuts**:
- `Ctrl+K`: Quick search
- `A`: Approve offer (in detail view)
- `R`: Request revision
- `E`: Edit offer
- `S`: Send to customer

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-06
**Feedback**: admin-docs@aigentics-corp.com
