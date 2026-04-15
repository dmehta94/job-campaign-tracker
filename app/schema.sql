/* Schema for the job-campaign-tracker application.
   Defines four tables: orgs, contacts, interactions, and applications.
*/

/* Stores organizations being tracked in the job search.
   category and lamp_list support filtering by org type and target list status.
   ON DELETE SET NULL on contacts and applications preserves records for removed orgs.
*/
CREATE TABLE IF NOT EXISTS orgs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    careers_url TEXT,
    category TEXT CHECK (category IN ('Civic Tech', 'Mission Aligned', 'Research & Policy', 'Enforcement & Accountability')),
    lamp_list INTEGER CHECK (lamp_list IN (0,1)),
    notes TEXT,
    created_date TEXT DEFAULT CURRENT_DATE
);

/* Stores contacts being tracked in the job search.
   Reach a contact on the platform provided with contact_value as the handle/address.
   capacity is a contact's professional capacity (peer, hiring manager, executive, etc.)
*/
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    org_id INTEGER REFERENCES orgs(id) ON DELETE SET NULL,
    platform TEXT,
    contact_value TEXT,
    capacity TEXT,
    status TEXT NOT NULL CHECK (status IN ('Contacted', 'Response Received', 'Never Responded', 'Referred and Recommended', 'Declined')) DEFAULT 'Contacted',
    next_follow_up_date TEXT,
    notes TEXT,
    created_date TEXT DEFAULT CURRENT_DATE
);

/* Stores interactions with contacts being tracked in the job search.
   ON DELETE CASCADE removes interaction records when the associated contact is deleted.
*/
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    interaction_type TEXT NOT NULL CHECK (interaction_type IN ('Outreach Established', 'Informational Interview', 'Referral Received', 'Coffee Chat', 'Reconnect')) DEFAULT 'Outreach Established',
    notes TEXT,
    date TEXT NOT NULL
);

/* Stores applications being tracked in the job search.
   referral_contact_id links an application to a referring contact where applicable.
*/
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY, 
    org_id INTEGER REFERENCES orgs(id) ON DELETE SET NULL,
    role_title TEXT NOT NULL, 
    job_url TEXT,
    date_applied TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Applied', 'ATS Screened', 'Recruiter Screened', 'Technical Screened', 'Interviewed', 'Offered', 'Accepted', 'Rejected by Org', 'Rejected Offer')) DEFAULT 'Applied',
    referral_contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
    follow_up_date TEXT,
    notes TEXT
);

/* Create indexes on foreign keys to improve query performance. */
CREATE INDEX idx_org_id ON contacts (org_id);
CREATE INDEX idx_contact_id ON interactions (contact_id);
CREATE INDEX idx_referral_contact_id ON applications (referral_contact_id);