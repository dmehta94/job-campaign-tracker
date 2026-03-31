from . import dashboard_bp

@dashboard_bp.route('/')
def index():
    return "Work in Progress"