from flask import render_template
from . import dashboard_bp
from ..database import get_db

@dashboard_bp.route('/')
def index():
    db = get_db()
    
    num_apps = db.execute(
        "SELECT COUNT(*) FROM applications"
    ).fetchone()[0]
    print(f'Applications Submitted: {num_apps}')

    progress = db.execute(
        "SELECT COUNT(*) FROM applications WHERE status IN ('Recruiter Screened', 'Technical Screened', 'Interviewed', 'Offered', 'Accepted', 'Rejected Offer')"
    ).fetchone()[0]
    print(f'Applications Progressed to Interview: {progress}')

    referred = db.execute(
        "SELECT COUNT(*) FROM interactions WHERE interaction_type = 'Referral Received'"
    ).fetchone()[0]
    print(f'Referrals Received: {referred}')

    return render_template('dashboard/index.html', num_apps = num_apps, progress = progress, referred = referred)